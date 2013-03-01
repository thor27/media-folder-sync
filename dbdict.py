import UserDict
import sqlite3
from sqlite3 import dbapi2 as sqlite
import os

class dbdict(UserDict.DictMixin):
    ''' dbdict, a dictionnary-like class that persists in a sqlite file 
        Thanks to: http://sebsauvage.net/python/snyppets/index.html#dbdict
    '''
    def __init__(self,db_filename):
        self.db_filename = db_filename
        
    def db_connect(self):
        if not os.path.isfile(self.db_filename):
            con = sqlite.connect(self.db_filename)
            con.execute("create table data (key PRIMARY KEY,value)")
        else:
            con = sqlite.connect(self.db_filename)
        return con
        
    def __getitem__(self, key):
        con = self.db_connect()
        row = con.execute("select value from data where key=?",(key,)).fetchone()
        con.close()
        if not row: raise KeyError
        return row[0]
   
    def __setitem__(self, key, item):
        con = self.db_connect()
        if con.execute("select key from data where key=?",(key,)).fetchone():
            con.execute("update data set value=? where key=?",(item,key))
        else:
            con.execute("insert into data (key,value) values (?,?)",(key, item))
        con.commit()
        con.close()
              
    def __delitem__(self, key):
        con = self.db_connect()
        if con.execute("select key from data where key=?",(key,)).fetchone():
            con.execute("delete from data where key=?",(key,))
            con.commit()
            con.close()
        else:
            con.close()
            raise KeyError
            
    def keys(self):
        con = self.db_connect()
        ret=[row[0] for row in con.execute("select key from data").fetchall()]
        con.close()
        return ret
