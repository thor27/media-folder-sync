#!/usr/bin/env python

import os
from pyinotify import WatchManager, IN_DELETE, IN_CREATE, IN_CLOSE_WRITE, ProcessEvent, Notifier
import sys
import subprocess
import tempfile
from optparse import OptionParser
from itertools import chain

# List of group of filetypes. Each dictionary in the list is all extensions 
# and codecs that needs to exist for this kind of file
filetypes = [
    {
        '.ogg': {'acodec':'libvorbis'},
        '.mp3': {'acodec':'libmp3lame'},
    },
]

# Store m_time of all files to check if the file has been updated by the user
# or by the system itself
filechecks = {}
check = lambda filepath: os.stat(filepath).st_mtime

def ffmpeg(file_in, file_out, codecs):
    """ Calls ffmeg to convert file_in to file_out using codecs
    """
    print "converting: %s -> %s" %(file_in,file_out)
    codecs = " ".join(["-%s %s" %(t,c) for t,c in codecs.items()])
    command = " ".join(["ffmpeg -y","-i '%s'" %file_in,codecs,"'%s'"%file_out])
    with tempfile.TemporaryFile() as tmp:
        exit_code = subprocess.call(command, stderr=tmp, shell=True)
        if exit_code !=0:
            tmp.seek(0)
            error_output = tmp.read()
            print "Error while converting."
            return error_output
    filechecks[file_out] = check(file_out)
    print "Done."
    
def get_type(extension):
    """ Return the group of filetypes, defined globally, that extension is
        part of.
    """ 
    for filetype in filetypes:
        if extension in filetype.keys():
            return filetype

def verify(filepath, ignore_check=False):
    """ Check if all the extensions has been created for filepath extension
        group, and creates if doesn't.
        Ignore check ignores the check from "filechecks" creating files if
        doesn't exists.
    """
    path, extension = os.path.splitext(filepath)
    filetype = get_type(extension)
    
    if not filetype:
        return
    
    print "File detected:",filepath
    if not ignore_check and filechecks.get(filepath,None) == check(filepath):
        return
    filechecks[filepath] = check(filepath)
    
    for ext,codecs in filetype.items():
        new_file = path+ext
        if new_file == filepath:
            continue
        
        if os.path.exists(new_file) and ignore_check:
            continue
        
        error = ffmpeg(filepath,new_file,codecs)
        if not error:
            continue
        
        with open(path+'.error','w') as error_file:
            error_file.write(error)
    
class Process(ProcessEvent):
    """ Process class that is connected to WatchManager.
        Everytime an event happens the specific method
        from this class is called.
    """
    def __init__(self, wm, mask):
        self.wm = wm
        self.mask = mask
        
    def process_IN_CREATE(self, event):
        path = os.path.join(event.path, event.name)
        if os.path.isdir(path):
            self.wm.add_watch(path, self.mask, rec=True)

    def process_IN_CLOSE_WRITE(self, event):
        filepath = os.path.join(event.path, event.name)
        verify(filepath)

def monitor_loop(folders):
    """ Main loop, create everything needed for the notification
        and waits for a notification. Loop again when notification
        happens.
    """
    wm = WatchManager()
    mask = IN_CLOSE_WRITE | IN_CREATE
    process = Process(wm, mask)
    notifier = Notifier(wm, process)
    for folder in folders:
        wdd = wm.add_watch(folder, mask, rec=True)
    try:
        while True:
            notifier.process_events()
            if notifier.check_events():
                notifier.read_events()
    except KeyboardInterrupt:
        notifier.stop()

def get_all_files(folder):
    """ Returns a generator that lists all files from a specific folder,
        recursively.
    """
    for dirpath, dirname, filenames in os.walk(folder):
        for filename in filenames:
            yield os.path.join(dirpath, filename)

def verify_all(folders):
    """ Calls verify for all files found on all specified folders
    """
    for filepath in chain(*map(get_all_files,folders)):
        verify(filepath, ignore_check=True)

def command_line_args():
    """ Deals with command line arguments
    """
    usage = "usage: %prog [options] folders"
    parser = OptionParser(usage=usage)
    parser.add_option("-v", "--no-verify", dest="verify", default=True,
        action="store_false", help="Does not verify all folders contents before start monitor")
    parser.add_option("-m", "--no-monitor", dest="monitor", default=True,
        action="store_false", help="Does not start folder monitor")
    return parser.parse_args()

def start():
    """ Starts application
    """
    options, folders = command_line_args()
    if not folders:
        folders.append(os.getcwd())
    if options.verify:
        print "Verifying existing files..."
        verify_all(folders)
        print "All files verified."
    if options.monitor:
        monitor_loop(folders)

if __name__ == "__main__":
    start()
