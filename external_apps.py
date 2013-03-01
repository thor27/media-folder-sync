import subprocess
from settings import ffmpeg_exec
import sys
import tempfile
import warnings

class Hook(object):
    def __init__(self):
        self._d = {}
    
    def add(self, name, script):
        self._d[name] = script
    
    def execute(self, name, *args):
        command = self._d.get(name,None)
        if not command:
            return
        proc = [command]+list(args)
        try:
            subprocess.call(proc)
        except Exception, e:
            warnings.warn(traceback.format_exc(),RuntimeWarning)
        

def ffmpeg(file_in, file_out, codecs):
    """ Calls ffmeg to convert file_in to file_out using codecs
    """
    print "converting: %s -> %s" %(file_in,file_out)
    codecs = " ".join(["-%s %s" %(t,c) for t,c in codecs.items()])
    command = " ".join([ffmpeg_exec,"-y","-i '%s'" %file_in,codecs,"'%s'"%file_out])
    with tempfile.TemporaryFile() as tmp:
        try:
            exit_code = subprocess.call(command, stderr=tmp, shell=True)
        except Exception, e:
            warnings.warn(traceback.format_exc(),RuntimeWarning)
        
        if exit_code !=0:
            tmp.seek(0)
            error_output = tmp.read()
            print "Error while converting."
            return command + '\n\n' + error_output
        
    print "conversion done."
