# List of group of filetypes. Each dictionary in the list is all extensions 
# and codecs that needs to exist for this kind of file
filetypes = [
    {
        '.mp4': {'vcodec':'mpeg4','acodec':'libmp3lame'},
        '.webm': {'vcodec':'libvpx','acodec':'libvorbis'},
    },
    {
        '.ogg': {'acodec':'libvorbis'},
        '.mp3': {'acodec':'libmp3lame'},
    },
]

# List of input formats, and to which format group it will be converted,
# by selecting any of the formats in the group.
# a regular expression will be used to match the whole filename
# ATTENTION: It is REGULAR EXPRESSION, not WILDCARD match
# this is only used when extesion is not a known filetype

input_formats = {
  '.*': '.mp4'
}

# FFmpeg executable name or path
ffmpeg_exec = 'ffmpeg'

#the max number of threads
number_of_threads = 5