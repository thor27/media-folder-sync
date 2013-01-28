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
