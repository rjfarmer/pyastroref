# SPDX-License-Identifier: GPL-2.0-or-later

import os
import re
import requests
import datetime
from pathlib import Path

from . import utils
from . import articles

class libraries(object):
    '''
    This is a collection of ADS libraries that supports iteration
    '''
    def __init__(self, adsdata):
        self.adsdata = adsdata
        self._data = None
        
    def update(self):
        data = requests.get(
                            utils.urls['libraries'],
                            auth=utils.BearerAuth(self.adsdata.token)
                            ).json()

        self._data = {}
        if 'libraries' in data:
            data = data['libraries']
        else:
            return

        # Repack data from list of dicts to dict of dicts
        self._data = {}
        for value in data:
            self._data[value['name']] = value

    def names(self):
        if self._data is None:
            self.update()
        x = list(self.keys())
        x.sort()
        return x

    def __getitem__(self, key):
        if self._data is None:
            self.update()
        if key in self._data.keys():
            return library(self.adsdata,self._data[key]['id'])

    def __getattr__(self, key):
        if self._data is None:
            self.update()
        if key in self._data.keys():
            return library(self.adsdata,self._data[key]['id'])

    def get(self, name):
        '''
        Fetches library
        '''
        return library(self.adsdata,self._data[name]['id'])

    def add(self, name, description='', public=False):
        '''
        Adds new library
        '''
        data = {
            'name':name,
            'public':public,
            'description':description
            }
        r = requests.post(
                            utils.urls['libraries'],
                            auth=utils.BearerAuth(self.adsdata.token),
                            headers={'Content-Type':'application/json'},
                            json = data
                        ).json()
        if 'name' not in r:
            raise ValueError(r['error'])
        self.update()

    
    def remove(self, name):
        '''
        Deletes library
        '''
        if name not in self._data.keys():
            raise KeyError('Library does not exit')

        lid = self._data[name]['id']

        requests.delete(
                            utils.urls['documents']+'/'+lid,
                            auth=utils.BearerAuth(self.adsdata.token)
                        )
        self._data.pop(name,None)


    def edit(self,name, name_new=None,description=None,public=False):
        '''
        Edit metadata of a given library
        '''
        if name not in self._data.keys():
            raise KeyError('Library does not exit')

        lid = self._data[name]['id']

        if name_new is not None:
            if len(name):
                name = name_new
        
        data = {
            'name':name,
            'public':public,
            'description':description
            }

        requests.put(
                        utils.urls['documents']+'/'+lid,
                        auth=utils.BearerAuth(self.adsdata.token),
                        headers={'Content-Type':'application/json'},
                        json = data
                    )


    def keys(self):
        if self._data is None:
            self.update()
        return self._data.keys()

    def __len__(self):
        if self._data is not None:
            return len(self._data)
        else:
            return 0

    def __contains__(self, key):
        if self._data is not None:
            return key in self._data
        else:
            return False

    def __iter__(self):
        for i in self._data:
            yield self.get(i)

    def __dir__(self):
        return ['reset','add','get','names','removes','update'] + list(self.keys())

    def values(self):
        return self._data.values()

    def items(self):
        return self._data.items()

class library(object):
    '''
    An instance of a single ADS library
    '''
    def __init__(self, adsdata, libraryid):
        self.adsdata = adsdata
        self.libraryid = libraryid
        self._data = []
        self.update()

    def url(self):
        return utils.urls['libraries'] + '/' + self.libraryid 

    def url_docs(self):
        return utils.urls['documents'] + '/' + self.libraryid 

    def update(self):
        self._data = []

        data = requests.get(
                            self.url(),
                            auth=utils.BearerAuth(self.adsdata.token)
                        ).json()
        self._data.extend(data['documents'])

        total_num = int(data['metadata']['num_documents'])
        if len(self._data) < total_num:
            num_left = total_num - len(self._data)
            data = requests.get(
                                self.url()+'?start='+str(len(self._data))+'&rows='+str(num_left),
                                auth=utils.BearerAuth(self.adsdata.token)
                            ).json()
            self._data.extend(data['documents'])

        self.metadata = data['metadata']
        self.name = self.metadata['name']

    def keys(self):
        return self._data

    @property
    def description(self):
        return self.metadata['description']

    def __getitem__(self,key):
        if key in self._data:
            return articles.article(self.adsdata,key)

    def __getattr__(self, key):
        if key in self.metadata.keys():
            return self.metadata[key]

    def __dir__(self):
        return self.metadata.keys() + ['keys','add','remove','get','update']

    def get(self, bibcode):
        return articles.article(self.adsdata,bibcode=bibcode)

    def add(self, bibcode):
        '''
        Add bibcode to library
        '''
        data = {'bibcode':self._ensure_list(bibcode),"action":"add"}
        r = requests.post(
                            self.url_docs(),
                            auth=utils.BearerAuth(self.adsdata.token),
                            headers={'Content-Type':'application/json'},
                            json = data
                        ).json()
        # Error check:
        if 'number_added' not in r:
            raise ValueError(r['message'])

    def remove(self, bibcode):
        '''
        Remove bibcode from library
        '''
        data = {'bibcode':self._ensure_list(bibcode),"action":"remove"}
        r = requests.post(
                            self.url_docs(),
                            auth=utils.BearerAuth(self.adsdata.token),
                            headers={'Content-Type':'application/json'},
                            json = data
                        ).json()
        # Error check:
        if 'number_removed' not in r:
            raise ValueError(r['message'])

    def __len__(self):
        return len(self._data)

    def __contains__(self, key):
        return key in self._data

    def __iter__(self):
        for i in self._data:
            yield self.get(i)

    # Just makes sure we have a list of strings
    def _ensure_list(self, s):
        return s if isinstance(s, list) else list(s)

    def __hash__(self):
        return hash(self.libraryid)

    def __eq__(self, value):
        if isinstance(value, library):
            if value.libraryid == self.libraryid:
                return True
        return False
