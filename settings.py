# List of group of filetypes. Each dictionary in the list is all extensions 
# and codecs that needs to exist for this kind of file
filetypes = [
    {
        '.ogg': {'acodec':'libvorbis'},
        '.mp3': {'acodec':'libmp3lame'},
    },
]

# FFmpeg executable name or path
ffmpeg_exec = 'ffmpeg'