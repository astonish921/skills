## 安装依赖
### 安装ffmpeg，否则mp4没有声音。下载好，系统环境变量Path添加这个bin所在的目录。处理好后，ffmpeg --version来验证一下。
下载地址：https://www.gyan.dev/ffmpeg/builds/#release-builds


### 安装yt-dlp
pip install yt-dlp

## 安装便捷工具
### 安装浏览器扩展插件 Cookie-Editor
用于导出b站cookies文件。edge/chrome都有插件的，edge的话搜索“Cookie-Editor”

## skill 安装方式
npx skills add https://github.com/astonish921/skills --skill bilibili-downloader

## 使用说明
### 创建文件夹用于下载视频
例如：D:\bili_down

### 导出b站cookies文件
浏览器访问b站，登录后，使用浏览器插件Cookie-Editor导出b站cookies文件，保存到D:\bili_down\cookies_www.bilibili.com.txt

### 下载视频
### 方式1，在编程工具，例如trae中输入提示词，其中，视频地址可以从打开的B站的视频里，右键获取：
/bilibili-downloader 下载B站视频：https://www.bilibili.com/video/BV11r4y1x7Nu?t=2.4，cookies文件：D:\bili_down\cookies_www.bilibili.com.txt，下载目录：D:\bili_down\，视频需要支持在iphone播放。python 环境使用 py310虚拟环境，通过conda activate py310 激活。



### 方式2，直接执行python
假设此skill安装在目前的目录：C:\Users\YH\.agents\skills\bilibili-downloader
```
python C:\Users\YH\.agents\skills\bilibili-downloader\bili_download.py --url "https://www.bilibili.com/video/BV11r4y1x7Nu?t=2.4" --output "D:\bili_down" --iphone --cookies "D:\bili_down\cookies_www.bilibili.com.txt"
```

### 参数说明

| 参数 | 说明 |
|------|------|
| `--url` | B站视频链接（支持BV号、完整URL） |
| `--space` | UP主UID，下载全部投稿 |
| `--output` | 输出目录，默认桌面 bilibili_downloads |
| `--audio-only` | 只保留MP3音频，删除视频 |
| `--vocals` | 同时生成纯人声MP3（去背景音乐，存入 vocals/ 子目录） |
| `--keep-video` | 提取音频同时保留视频文件 |
| `--all-pages` | 下载合集所有分P |
| `--cookies` | 使用浏览器cookies |
| `--iphone` | 下载iPhone版本视频 （默认合成的视频格式为视频编码格式AV1，不被 iPhone 原生支持，iphone的话需要转为MP4） |

## 注意事项
1、如果使用了python虚拟环境，要在提示词里说明如何激活并使用虚拟环境，例如：。python 环境使用 py310虚拟环境，通过conda activate py310 激活。


