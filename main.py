import os
import sys
import time
import shutil
import base64
import bencode
import requests
import subprocess
from deluge_client import DelugeRPCClient


BATCH_SIZE = 10
DOWNLOAD_DIR = '/path/to/deluge/download/folder'
UPLOAD_COMMAND = 'rclone copy "$src" "onedrive:torrents/$src" --onedrive-chunk-size 50M --bwlimit 120M --transfers 8'
DELUGE_CONFIG = {
    'host': '127.0.0.1',
    'port': 58846,
    'username': 'localclient',
    'password': '5a20c4069c796107b160aec21fad40bf5c83ca88',
}


class Downloader:
    def __init__(self):
        self.deluge = DelugeRPCClient(
            host=DELUGE_CONFIG['host'],
            port=DELUGE_CONFIG['port'],
            username=DELUGE_CONFIG['username'],
            password=DELUGE_CONFIG['password'],
            decode_utf8=True
        )

    def add(self, torrent):
        if not os.path.isfile(torrent):
            r = requests.get(torrent)
            torrent = r.content
        else:
            with open(torrent, 'rb') as f:
                torrent = f.read()

        data = bencode.bdecode(torrent)
        info = data[b'info']
        self.torrent_name = info[b'name'].decode('utf-8')
        if b'files' in info:
            self.single_file = False
            largest = max([x[b'length'] for x in info[b'files']])
        else:
            self.single_file = True
            largest = info[b'length']

        if largest > BATCH_SIZE * 1024 ** 3:
            print('ERROR: Torrent too large!')
            sys.exit(1)

        filename = self.torrent_name + '.torrent'
        filedump = base64.b64encode(torrent)
        self.hash = self.deluge.call('core.add_torrent_file',
                                     filename, filedump, {'add_paused': True})

    def pause(self):
        self.deluge.call('core.pause_torrent', [self.hash])

    def resume(self):
        self.deluge.call('core.resume_torrent', [self.hash])

    def remove(self):
        self.deluge.call('core.remove_torrent', self.hash, True)

    def get_files(self):
        info = self.deluge.call('core.get_torrents_status', {
                                'hash': self.hash}, ['files'])
        return info[self.hash]['files']

    def get_file_progress(self):
        info = self.deluge.call('core.get_torrents_status', {
                                'hash': self.hash}, ['file_progress'])
        return info[self.hash]['file_progress']

    def set_file_priorities(self, priorities):
        self.deluge.call('core.set_torrent_file_priorities',
                         self.hash, priorities)

    def download(self):
        file_list = self.get_files()
        download_list = []

        def down():
            priorities = [1 if x in download_list else 0 for x in file_list]
            self.set_file_priorities(tuple(priorities))
            self.resume()

            while True:
                progress = self.get_file_progress()
                sum = 0
                for i in download_list:
                    sum += progress[i['index']]
                if sum < len(download_list):
                    time.sleep(5)
                else:
                    break

            self.pause()

            src = self.torrent_name
            cmd = UPLOAD_COMMAND.replace('$src', src)
            subprocess.check_output(cmd, shell=True, cwd=DOWNLOAD_DIR)

            path = os.path.join(DOWNLOAD_DIR, src)
            try:
                if os.path.isfile(path):
                    os.remove(path)
                else:
                    shutil.rmtree(path)
            except FileNotFoundError:
                pass

        total = 0
        for file in file_list:
            size = file['size']
            if total + size <= BATCH_SIZE * 1024 ** 3:
                total += size
            else:
                down()
                total = size
                download_list.clear()
            download_list.append(file)
        if download_list:
            down()

        self.remove()


if __name__ == '__main__':
    torrent = sys.argv[1]
    d = Downloader()
    d.add(torrent)
    d.download()
