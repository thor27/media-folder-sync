The MFS - Media Folder Sync GitHub page
=======================================

For improved html5 support, most servers needs to keep 2 or more copys of your media file in different formats. This script monitors a specific folder, using Linux Inotify for changes, and uses ffmpeg to convert your video/audio for all formats wanted.
<br/>
This version here keeps an ogg and mp3 version for all submited audios (in ogg or mp3 format).
To modify or improve this, edit settings.py and update the filetypes list.
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

Tips with FFMPEG
----------------
ffmpeg is an awesome tool for video/audio converting, but it's also commonly distributed without all his capabilities, mostly because of legal reasons in USA and some other countries.
To know which containers your instalation of ffmpeg supports, type this:
```
ffmpeg -format
```
And for a list of codecs:
```
ffmpeg -codecs
```
A simple tip on how to get a very complete ffmpeg on Debian:
```
#Remove your existing installation of ffmpeg
apt-get remove --purge ffmpeg 

#This ubuntu mirrors has some codec dev packages, you can also remove it after the apt-get install if you prefer
echo 'deb http://archive.ubuntu.com/ubuntu natty main restricted universe multiverse' >/etc/apt/sources.list.d/ubuntu.list
apt-get update
apt-get install make automake g++ bzip2 python unzip patch subversion ruby build-essential git-core checkinstall yasm texi2html libfaac-dev libmp3lame-dev libopencore-amrnb-dev libopencore-amrwb-dev libsdl1.2-dev libtheora-dev libvdpau-dev libvorbis-dev libvpx-dev libx11-dev libxfixes-dev libxvidcore-dev zlib1g-dev

git clone git://git.videolan.org/x264.git
cd x264

#This disable-asm is only important if, without it, the configure complains about an old asm compiler.
./configure --enable-shared --disable-asm 
make
make install
cd ..

wget http://webm.googlecode.com/files/libvpx-v0.9.7-p1.tar.bz2
tar -xjf libvpx-v0.9.7-p1.tar.bz2
cd libvpx-v0.9.7-p1
./configure
make
make install
cd ..
ldconfig

git clone git://source.ffmpeg.org/ffmpeg
cd ffmpeg
./configure --enable-gpl --enable-version3 --enable-nonfree --enable-postproc --enable-libfaac --enable-libmp3lame --enable-libopencore-amrnb --enable-libopencore-amrwb --enable-libtheora --enable-libvorbis --enable-libvpx --enable-libx264 --enable-libxvid --enable-x11grab
make
make install
cd ..

ldconfig
```

Deploy example on Debian with Supervisor
----------------------------------------
Here is a deploy example of media-sync on debian, considering you already have ffmpeg installed (see above for a ffmpeg tip)
```
apt-get install python-virtualenv python-pyinotify
cd /opt
mkdir media-folder-sync
cd media-folder-sync
virtualenv vpython-mfs
. vpython-mfs/bin/activate
pip install supervisor
git clone https://github.com/thor27/media-folder-sync.git
echo_supervisord_conf > /etc/supervisord.conf
vim /etc/supervisord.conf
```
At the end of the file, add:
```
[program:mfs]
command=/opt/media-folder-sync/vpython-mfs/bin/python /opt/media-folder-sync/media-folder-sync/media_folder_sync.py /var/www/files/ -d /opt/media-folder-sync/database.db
```
Replace the path /var/www/files/ with the folder you want to monitor with MFS.
Now, create links for supervisor executables:
```
ln -s `pwd`/vpython-mfs/bin/supervisorctl /usr/local/bin/
ln -s `pwd`/vpython-mfs/bin/supervisord /usr/local/bin/
deactivate
```
So, to start supervisor just run supervisord
```
supervisord
```
To check if media-folder-sync is running, or to start/stop it, just use supervisorctl
```
supervisorctl status mfs
supervisorctl start mfs
supervisorctl stop mfs
supervisorctl restart mfs
```
To stop supervisor process (and also media-folder-sync):
```
supervisorctl shutdown
```
More info on how to use or configure supervisor, go to the official website: <a href="http://supervisord.org/">http://supervisord.org/</a>
