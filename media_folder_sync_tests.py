try:
    import unittest2 as unittest
    TIMEWAIT=1
except ImportError:
    import unittest
    TIMEWAIT=0.1
import media_folder_sync as mfs
import tempfile
import os, stat
import shutil

class db_dict_test(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp()
        self.create_db = lambda : mfs.dbdict(os.path.join(self.directory,'db.db'))
        self.close_db = lambda db: db.con.close()
    
    def tearDown(self):
        shutil.rmtree(self.directory, ignore_errors=True)
    
    def test_has_key(self):
        db = self.create_db()
        db['test'] = 'value'
        self.assertTrue(db.has_key('test'))
        self.close_db(db)
        db2 = self.create_db()
        self.assertTrue(db2.has_key('test'))
        self.close_db(db2)
    
    def test_del(self):
        db = self.create_db()
        db['test'] = 'value'
        del db['test']
        self.assertFalse(db.has_key('test'))
        self.close_db(db)
        db2 = self.create_db()
        self.assertFalse(db2.has_key('test'))
        self.close_db(db2)
    
    def test_value(self):
        db = self.create_db()
        db['test'] = 'value'
        self.assertEqual(db['test'], 'value')
        self.close_db(db)
        db2 = self.create_db()
        self.assertEqual(db2['test'], 'value')
        self.close_db(db2)
    
    def test_get_method(self):
        db = self.create_db()
        db['test'] = 'value'
        self.assertEqual(db.get('test',None), 'value')
        self.assertIsNone(db.get('test2',None))
        self.close_db(db)
        db2 = self.create_db()
        self.assertEqual(db2.get('test',None), 'value')
        self.assertIsNone(db2.get('test2',None))
        self.close_db(db2)
    
    def test_for_in(self):
        db = self.create_db()
        db['test'] = 'value'
        db['test2'] = 'value2'
        array = [ x for x in db ]
        self.assertIn('test', array)
        self.assertIn('test2', array)
        self.assertNotIn('test3', array)
        self.close_db(db)
        db2 = self.create_db()
        array2 = [ x for x in db2 ]
        self.assertIn('test', array2)
        self.assertIn('test2', array2)
        self.assertNotIn('test3', array2)
        self.close_db(db2)
    
class mfs_test(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.mkdtemp()
        filenames = ['1.a','2.a','3.a','1.b','2.b','1.c','2.c','1.d']
        self.filenames = [os.path.join(self.directory,f) for f in filenames]
        for filename in self.filenames:
            with open(filename,'w') as openfile:
                openfile.write('')
            mfs.filechecks[filename] = mfs.check(filename)
        
        self._oldfiletypes = mfs.filetypes
        mfs.filetypes = [
            {
                '.a': {'acodec':'aliba','vcodec':'vliba'},
                '.b': {'acodec':'alibb','vcodec':'vlibb'},
            },
            {
                '.c': {'acodec':'alibc','vcodec':'vlibc'},
                '.d': {'acodec':'alibd','vcodec':'vlibd'},
            },
        ]
        ffmpeg_exec = os.path.join(self.directory,'ffmpeg.sh')
        with open(ffmpeg_exec,'w') as script:
            script.write("""
                #!/bin/bash
                cd "`dirname $0`"
                > ffmpeg.result
                for x in "$@"
                do
                   echo $x >> ffmpeg.result
                done
                echo cp "$3" "$8"
                cp "$3" "$8"
            """);
        os.chmod(ffmpeg_exec, stat.S_IXUSR | stat.S_IRUSR | stat.S_IWUSR)
        self.old_ffmpeg = mfs.ffmpeg_exec
        mfs.ffmpeg_exec = ffmpeg_exec
        
    def tearDown(self):
        #shutil.rmtree(self.directory, ignore_errors=True)
        mfs.filetypes = self._oldfiletypes
        mfs.filechecks = {}
        mfs.ffmpeg_exec = self.old_ffmpeg
        
    def test_remove_related_files(self):
        mfs.remove_related_files(self.filenames[0])
        self.assertFalse(os.path.exists(self.filenames[0]))
        self.assertFalse(os.path.exists(self.filenames[3]))
        self.assertFalse(mfs.filechecks.has_key(self.filenames[0]))
        self.assertFalse(mfs.filechecks.has_key(self.filenames[3]))
    
    def test_ffmpeg(self):
        print 'the bash is: ',mfs.ffmpeg_exec
        mfs.ffmpeg(
            self.filenames[0],
            self.filenames[1],
            {'acodec':'aliba','vcodec':'vliba'}
        )
        with open(os.path.join(self.directory,'ffmpeg.result')) as f:
            lines = [l.replace('\n','') for l in f]
        self.assertEqual(lines[0],'-y')
        self.assertEqual(lines[1],'-i')
        self.assertEqual(lines[2],self.filenames[0])
        self.assertEqual(lines[3],'-vcodec')
        self.assertEqual(lines[4],'vliba')
        self.assertEqual(lines[5],'-acodec')
        self.assertEqual(lines[6],'aliba')
        self.assertEqual(lines[7],self.filenames[1])
    
    def test_gettype(self):
        filetype = mfs.get_type('.b')
        self.assertEqual(filetype,mfs.filetypes[0])
        filetype = mfs.get_type('.c')
        self.assertEqual(filetype,mfs.filetypes[1])
    
    def test_verify(self):
        from time import sleep
        sleep(TIMEWAIT) #to get a different mtime on file
        with open(self.filenames[2],'w') as f:
            f.write('new data')
        mfs.verify(self.filenames[2])
        new_file = os.path.join(self.directory,'3.b')
        self.assertTrue(os.path.exists(new_file))
        with open(new_file) as f:
            data = f.read()
        self.assertEquals(data,'new data')
    
    def test_verify_all(self):
        mfs.filechecks = {}
        filenames = ['1.a','2.a','3.a','1.b','2.b','3.b','1.c','2.c','1.d','2.d']
        filenames = [os.path.join(self.directory,f) for f in filenames]
        mfs.verify_all([self.directory])
        for filename in filenames:
            self.assertTrue(os.path.exists(filename))
    
if __name__ == '__main__':
    unittest.main()