# SPDX-License-Identifier: GPL-2.0-or-later

import sqlite3
import os
import collections

try:
    from . import utils
except:
    import utils

_fields = ['bibcode', 'arxiv', 'title', 'abstract', 'first_author', 
            'authors', 'filename', 'year','pubdate', 'journal', 'bibtex']

class database(object):
    def __init__(self):
        self.dbname = os.path.join(utils.db_read(),'pyastroref.db')
        self.connect()
        self.create()

    def fields(self):
        return _fields

    def connect(self):
        self.conn = sqlite3.connect(self.dbname)
        self.conn.row_factory = sqlite3.Row

    def indb(self, bibcode):
        cursor = self.conn.cursor()
        cursor.execute('SELECT bibcode from papers WHERE bibcode=?',(bibcode,))
        return cursor.fetchone() is not None

    def add(self,data,editable=False):
        cursor = self.conn.cursor()
        # Is bibcode allready in db?
        if self.indb(data['bibcode']):
            if editable:
                for key,value in data:
                    if len(value):
                        cursor.execute(
                            "UPDATE papers SET {}=? WHERE bibcode=?".format(key),(value, data['bibcode'])
                            )
                        self.conn.commit()
        else:
            cursor.execute(
                "INSERT INTO papers VALUES ("+','.join(["?"]*len(_fields))+")",
                            tuple(data[i] for i in _fields)
                )
            self.conn.commit()


    def get_field(self, bibcode, field):
        cursor = self.conn.cursor()
        cursor.execute('SELECT ? from papers WHERE bibcode=?',(field, bibcode))
        row = cursor.fetchone()
        return row[field]

    def get_one(self, bibcode):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * from papers WHERE bibcode=?',(bibcode,))
        return cursor.fetchone()

    def get_all(self):
        cursor = self.conn.cursor()
        cursor.execute('SELECT * from papers')
        return cursor.fetchall()

    def get_bibtext(self, bibcode):
        return self.get_field(bibcode,'bibtex')

    def get_filename(self, bibcode):
        return self.get_field(bibcode,'filename')

    def create(self):
        cursor = self.conn.cursor()
        if not self.iftablexists():
            cursor.execute('CREATE TABLE papers ('+','.join(_fields)+')',)
            self.conn.commit()

    def iftablexists(self):
        cursor = self.conn.cursor()
        try:
            cursor.execute("SELECT bibcode from papers")
            x = True
        except sqlite3.OperationalError:
            x = False

        return x

    def __del__(self):
        self.conn.close()