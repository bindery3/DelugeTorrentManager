# DelugeTorrentManager
下载种子并上传到网盘，对大于硬盘空间的种子中的文件分批下载
> e.g. 在只有 20G 的小鸡上下载 TLMC 并上传到 OneDrive

## 配置
```
BATCH_SIZE       // 每次下载的文件大小，应大于种子中最大文件（单位：GiB）
DOWNLOAD_DIR     // Deluge 下载目录，仅用于在上传时定位文件，种子将下载到 Deluge 默认下载目录
UPLOAD_COMMAND   // Rclone、OneDriveUploader 等工具的上传命令，$src 为占位符，表示源文件或目录
DELUGE_CONFIG    // Deluge 连接配置
```

## 示例
#### UPLOAD_COMMAND

Rclone:
```
rclone copy "$src" "onedrive:torrents/$src" --onedrive-chunk-size 50M --bwlimit 120M --transfers 8
```

OneDriveUploader:
```
OneDriveUploader -f -c "auth.json" -s "$src" -r "torrents"
```

#### 运行

从文件添加种子：
```
python3 main.py test.torrent
```
从链接添加种子：
```
python3 main.py https://example.com/test.torrent
```

