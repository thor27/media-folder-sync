#!/usr/bin/env python

import os
from pyinotify import WatchManager, IN_DELETE, IN_CREATE, IN_CLOSE_WRITE, ProcessEvent, Notifier
import sys
import subprocess
import tempfile
from optparse import OptionParser
from itertools import chain
import sqlite3
import UserDict
from sqlite3 import dbapi2 as sqlite

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

class dbdict(UserDict.DictMixin):
    ''' dbdict, a dictionnary-like class that persists in a sqlite file 
        Thanks to: http://sebsauvage.net/python/snyppets/index.html#dbdict
    '''
    def __init__(self,db_filename):
        self.db_filename = db_filename
        if not os.path.isfile(self.db_filename):
            self.con = sqlite.connect(self.db_filename)
            self.con.execute("create table data (key PRIMARY KEY,value)")
        else:
            self.con = sqlite.connect(self.db_filename)
   
    def __getitem__(self, key):
        row = self.con.execute("select value from data where key=?",(key,)).fetchone()
        if not row: raise KeyError
        return row[0]
   
    def __setitem__(self, key, item):
        if self.con.execute("select key from data where key=?",(key,)).fetchone():
            self.con.execute("update data set value=? where key=?",(item,key))
        else:
            self.con.execute("insert into data (key,value) values (?,?)",(key, item))
        self.con.commit()
              
    def __delitem__(self, key):
        if self.con.execute("select key from data where key=?",(key,)).fetchone():
            self.con.execute("delete from data where key=?",(key,))
            self.con.commit()
        else:
             raise KeyError
            
    def keys(self):
        return [row[0] for row in self.con.execute("select key from data").fetchall()]

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
    for ext in filetype:
        filepath=path+ext
        print "deleting:", filepath
        if filechecks.has_key(filepath):
            del filechecks[filepath]
        if os.path.exists(filepath):
            os.remove(filepath)

def ffmpeg(file_in, file_out, codecs):
    """ Calls ffmeg to convert file_in to file_out using codecs
    """
    print "converting: %s -> %s" %(file_in,file_out)
    codecs = " ".join(["-%s %s" %(t,c) for t,c in codecs.items()])
    command = " ".join([ffmpeg_exec,"-y","-i '%s'" %file_in,codecs,"'%s'"%file_out])
    with tempfile.TemporaryFile() as tmp:
        exit_code = subprocess.call(command, stderr=tmp, shell=True)
        if exit_code !=0:
            tmp.seek(0)
            error_output = tmp.read()
            print "Error while converting."
            return error_output
    print "conversion done."
    
def get_type(extension):
    """ Return the group of filetypes, defined globally, that extension is part of.
    """
    for filetype in filetypes:
        if extension in filetype.keys():
            return filetype

def verify(filepath):
    """ Check if all the extensions has been created for filepath extension
        group, and creates if doesn't.
    """
    path, extension = os.path.splitext(filepath)
    filetype = get_type(extension)
    
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
    
    for ext,codecs in filetype.items():
        new_file = path+ext
        
        if new_file == filepath:
            continue
        
        if filecheck == None and os.path.exists(new_file):
            print 'A unknown file detected: %s. Assuming it is correct.' %new_file
            filechecks[new_file] = check(new_file)
            continue
        
        error = ffmpeg(filepath,new_file,codecs)

        if error:
            with open(path+'.error','w') as error_file:
                error_file.write(error)
            continue
        
        filechecks[new_file] = check(new_file)

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
    # Add/Update all files
    for filepath in chain(*map(get_all_files,folders)):
        verify(filepath)
    
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
        verify(filepath)
    
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
        
    return parser.parse_args()

def start():
    """ Starts application
    """
    global filechecks
    options, folders = command_line_args()
    filechecks = dbdict(options.database)
    
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
