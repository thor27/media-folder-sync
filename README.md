media_folder_sync
=================

For improved html5 support, most servers needs to keep 2 or more copys of your media file in different formats. This script monitors a specific folder, using Linux Inotify for changes, and uses ffmpeg to convert your video/audio for all formats wanted.
<br/>
This version here keeps an ogg and mp3 version for all submited audios (in ogg or mp3 format).
To modify or improve this, edit media_folder_sync.py and update the filetypes list.
Each dictionay inside filetypes list mean a group of media elements with it's ffmpeg codec.
Lets say that you need to have, for audio, formats mp3 and ogg and for video webm and mp4. You will do something like that:

```
filetypes = [
    {
        '.ogg': {'acodec':'libvorbis'},
        '.mp3': {'acodec':'libmp3lame'},
    },
    {
        '.mp4': {'vcodec':'mpeg4','acodec':'libvo_aacenc'},
        '.webm': {'vcodec':'libvpx','acodec':'libvorbis'},
    },
]
```
to use it, you just need to call the script and after the folder you want to monitor. This script will monitor all folder recursively, but WILL NOT follow symlinks.
```
./media_folder_sync.py /var/www/media
```

To use in production, a tool like <a href="http://supervisord.org/">Supervisor</a> is highly recommended.
