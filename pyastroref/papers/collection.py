# SPDX-License-Identifier: GPL-2.0-or-later

import os
import re
import requests
import datetime
from pathlib import Path

from . import utils
from . import articles


class Collection(object):
    _url = 'http://adsabs.harvard.edu/abs_doc/journals1.html'

    _init_default_journals = {
        'Astronomy and Astrophysics':'A&A',
        'The Astrophysical Journal':'ApJ',
        'The Astrophysical Journal Supplement Series':'ApJS',
        'Monthly Notices of the Royal Astronomical Society':'MNRAS',
        'Nature':'Natur',
        'Nature Astronomy':'NatAs',
        'Science':'Sci'
    }

    default_journals = {}

    _file_all = Path(utils.settings['ALL_JOURNALS_LIST'])
    _file = Path(utils.settings['JOURNALS_LIST'])

    def __init__(self, token):
        self.token = token
        self.all_journals = {}
        self._results = {}

        self.load_defaults()

        self.update_journals()


    def load_defaults(self):
        if not os.path.exists(self._file):
            self.default_journals = self._init_default_journals
            return

        self.default_journals = self.read_file(self._file)



    def if_update_journal(self):
        if not os.path.exists(self._file_all):
            return True

        last_week = datetime.date.today() - datetime.timedelta(days=7)
        last_modified = datetime.date.fromtimestamp(self._file_all.stat().st_mtime)
        if last_modified < last_week:
            return True

        return False

    def update_journals(self):
        if self.if_update_journal():
            self.make_file()

        self.all_journals = self.read_file(self._file_all)
        # Remove default journals
        for k in self.default_journals.keys():
            self.all_journals.pop(k, None)


    def make_file(self):
        r = requests.get(self._url)
        data = r.content.decode().split('\n')
        
        res = {}
        for line in data:
            if line.startswith('<a href="#" onClick='):
                _, journ_short, name = line.split('>')
                journ_short = journ_short.split()[0].strip()
                name = name.strip()
                res[name] = journ_short

        with open(self._file_all,'w') as f:
            for key,value in res.items():
                print(key,value,file=f)

    def read_file(self, filename):
        all_journals = {}
        with open(filename,'r') as f:
            for line in f.readlines():
                l = line.split()
                value = l[-1]
                key = ' '.join(l[:-1])
                all_journals[key.strip()] = value.strip()
        return all_journals


    def save_defaults(self):
        with open(self._file,'w') as f:
            for key,value in self.default_journals.items():
                print(key,value,file=f)

    def list_defaults(self):
        return self.default_journals.keys()

    def list_all(self):
        return self.all_journals.keys()

    def search(self, name):
        for value in self.default_journals:
            if value == name:
                break

        if name not in self._results:
            today = datetime.date.today()
            monthago = today - datetime.timedelta(days=31)

            pubdata = "pubdate:["
            pubdata+= str(monthago.year) +"-"+ str(monthago.month).zfill(2)
            pubdata+= ' TO '
            pubdata+= str(today.year) +"-"+ str(today.month).zfill(2)
            pubdata+=']'

            query = 'bibstem:"'+name+'" AND '+pubdata

            self._results[name] = articles.search(self.token).search(query)

        return self._results[name]
