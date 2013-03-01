#!/usr/bin/env python

import os
import re
from pyinotify import WatchManager, IN_DELETE, IN_CREATE, IN_CLOSE_WRITE, ProcessEvent, Notifier
from optparse import OptionParser
from itertools import chain
from dbdict import dbdict
from settings import *
from external_apps import Hook, ffmpeg
import lock
import threading
from time import sleep

hook = Hook()

# Store m_time of all files to check if the file has been updated by the user
# or by the system itself
filechecks = {}
check = lambda filepath: os.stat(filepath).st_mtime

def remove_related_files(filepath):
    """ Remove filepath and related files (from the same name and group of
        extension) from filesystem and filechecks
    """
    path, extension = os.path.splitext(filepath)
    filetype = get_type(extension)
    if not filetype:
        filetype=verify_input(filepath)
    
    print "deleting:", filepath
    if filechecks.has_key(filepath):
        del filechecks[filepath]
    if os.path.exists(filepath):
        os.remove(filepath)

    for ext in filetype:
        filepath=path+ext
        print "deleting:", filepath
        if filechecks.has_key(filepath):
            del filechecks[filepath]
        if os.path.exists(filepath):
            os.remove(filepath)
    
def get_type(extension):
    """ Return the group of filetypes, defined globally, that extension is 
        part of.
    """
    for filetype in filetypes:
        if extension in filetype.keys():
            return filetype

def verify_input(filepath):
    """ Check if filepath is an input file
    """
    path, extension = os.path.splitext(filepath)
    
    for regext, ext in input_formats.items():
        if not re.match(regext,filepath):
            continue
        filetype = get_type(ext)
        if not filetype:
            continue
        return filetype

def start_thread(filepath):
    if filepath.endswith('.error') or filepath.endswith('.lock'):
        return
    
    if not lock.get_lock(filepath):
        return
    
    while threading.activeCount() > number_of_threads:
        print 'too many threads, waiting for one to finish.'
        sleep(1)
        
    t=threading.Thread(target=verify, args=(filepath,))
    t.start()

@lock.release_lock_decorator
def verify(filepath):
    """ Check if all the extensions has been created for filepath extension
        group, and creates if doesn't.
    """
    path, extension = os.path.splitext(filepath)

    filetype = get_type(extension)
    
    if not filetype:
        filetype=verify_input(filepath)
        if not filetype:
            return
    
    filecheck = filechecks.get(filepath,None)
    
    if  filecheck == check(filepath):
        return
    
    if filecheck:
        print "File change detected:",filepath
    else:
        print "New file detected:",filepath
    
    filechecks[filepath] = check(filepath)
    filenames = [filepath]
    for ext,codecs in filetype.items():
        new_file = path+ext
        
        if new_file == filepath:
            continue
        
        filenames.append(new_file)
        
        if filecheck == None and os.path.exists(new_file):
            print 'Unknown file detected: %s. Assuming it is correct.' %new_file
            filechecks[new_file] = check(new_file)
            continue
        
        error = ffmpeg(filepath,new_file,codecs)

        if error:
            with open(path+'.error','w') as error_file:
                error_file.write(error)
            continue
        
        filechecks[new_file] = check(new_file)
        hook.execute('hook_each', new_file)
        
    hook.execute('hook_all', *filenames)


def get_all_files(folder):
    """ Returns a generator that lists all files from a specific folder,
        recursively.
    """
    for dirpath, dirname, filenames in os.walk(folder):
        for filename in filenames:
            yield os.path.join(dirpath, filename)

def verify_all(folders):
    """ Calls verify for all files found on all specified folders,
        and remove all non existant files.
    """
    
    #release all locks
    for filepath in chain(*map(get_all_files,folders)):
        if lock.release_lock(filepath):
            lockname = lock.get_lockfilename(filepath)
            print 'Stalled lock file "%s", removed.' %lockname
    
    # Add/Update all files
    for filepath in chain(*map(get_all_files,folders)):
        start_thread(filepath)
    
    #Remove non existant files
    for filepath in filechecks:
        if not os.path.exists(filepath):
            remove_related_files(filepath)
    
class Process(ProcessEvent):
    """ Process class that is connected to WatchManager.
        Everytime an event happens the specific method
        from this class is called.
    """
    def __init__(self, wm, mask):
        self.wm = wm
        self.mask = mask
        
    def process_IN_CREATE(self, event):
        """ File or directory has been created.
            If a folder is created, add it to be monitored
        """
        path = os.path.join(event.path, event.name)
        if os.path.isdir(path):
            self.wm.add_watch(path, self.mask, rec=True)

    def process_IN_CLOSE_WRITE(self, event):
        """ File has been closed after a write.
            The verification is done here to make sure
            that everything was written to the file before
            any conversion starts
        """
        filepath = os.path.join(event.path, event.name)
        start_thread(filepath)
    
    def process_IN_DELETE(self, event):
        """ File or directory has been deleted.
            If a file is deleted, remove it from filechecks
        """
        filepath = os.path.join(event.path, event.name)
        if filechecks.has_key(filepath):
            remove_related_files(filepath)
        
def monitor_loop(folders):
    """ Main loop, create everything needed for the notification
        and waits for a notification. Loop again when notification
        happens.
    """
    wm = WatchManager()
    mask = IN_CLOSE_WRITE | IN_CREATE | IN_DELETE
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

def command_line_args():
    """ Deals with command line arguments
    """
    usage = "usage: %prog [options] folders"
    parser = OptionParser(usage=usage)
    parser.add_option("-v", "--no-verify", dest="verify", default=True,
        action="store_false", help="Does not verify all folders contents before start monitor")
    parser.add_option("-m", "--no-monitor", dest="monitor", default=True,
        action="store_false", help="Does not start folder monitor")
    parser.add_option("-d", "--database", dest="database", default=os.path.expanduser('~/.media-folder-sync.db'),
        help="Change SQLite database file")
    parser.add_option("-a", "--after_conversion", dest="hook_each", default=None,
        help="Script to be executed after each successful conversion. Converted file will be the argument")    
    parser.add_option("-A", "--after_all_conversions", dest="hook_all", default=None,
        help="Script to be executed after all conversions for a new/modified file is done. The original filename, and all group filenames will be passed as argument.")    
    
    return parser.parse_args()

def start():
    """ Starts application
    """
    global filechecks
    options, folders = command_line_args()
    filechecks = dbdict(options.database)
    if options.hook_all:
        hook.add('hook_all',options.hook_all)
    
    if options.hook_each:
        hook.add('hook_each',options.hook_each)
    
    if not folders:
        folders.append(os.getcwd())
    
    folders = [os.path.abspath(folder) for folder in folders]
    
    if options.verify:
        print "Verifying existing files..."
        verify_all(folders)
        print "All files verified."
        
    if options.monitor:
        monitor_loop(folders)

if __name__ == "__main__":
    start()
