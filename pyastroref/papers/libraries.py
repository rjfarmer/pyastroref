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
    def __init__(self, token):
        self.token = token
        self.data = None
        self._n = 0
        
    def update(self):
        data = requests.get(
                                utils.urls['libraries'],
                                auth=utils.BearerAuth(self.token)
                            ).json()

        data = data['libraries']

        # Repack data from list of dicts to dict of dicts
        self.data = {}
        for value in data:
            self.data[value['name']] = value

    def names(self):
        if self.data is None:
            self.update()
        x = list(self.keys())
        x.sort()
        return x

    def __getitem__(self, key):
        if self.data is None:
            self.update()
        if key in self.data.keys():
            return library(self.token,self.data[key]['id'])

    def __getattr__(self, key):
        if self.data is None:
            self.update()
        if key in self.data.keys():
            return library(self.token,self.data[key]['id'])

    def get(self, name):
        '''
        Fetches library
        '''
        return library(self.token,self.data[name]['id'])

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
                            auth=utils.BearerAuth(self.token),
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
        if name not in self.data.keys():
            raise KeyError('Library does not exit')

        lid = self.data[name]['id']

        requests.delete(
                            utils.urls['documents']+'/'+lid,
                            auth=utils.BearerAuth(self.token)
                        )
        self.data.pop(name,None)


    def edit(self,name, name_new=None,description=None,public=False):
        '''
        Edit metadata of a given library
        '''
        if name not in self.data.keys():
            raise KeyError('Library does not exit')

        lid = self.data[name]['id']

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
                        auth=utils.BearerAuth(self.token),
                        headers={'Content-Type':'application/json'},
                        json = data
                    )


    def keys(self):
        if self.data is None:
            self.update()
        return self.data.keys()

    def __len__(self):
        if self.data is not None:
            return len(self.data)
        else:
            return 0

    def __contains__(self, key):
        if self.data is not None:
            return key in self.data
        else:
            return False

    def __iter__(self):
        return self

    def __next__(self):
        if self.data is None:
            self.update()

        if self._n >= len(self.data):
            raise StopIteration

        res = self.get(self.keys()[self._n])
        self._n +=1
        return res

    def reset(self):
        self._n = 0

    def __dir__(self):
        return ['reset','add','get','names','removes','update'] + list(self.keys())

class library(object):
    '''
    An instance of a single ADS library
    '''
    def __init__(self, token, libraryid):
        self.token = token
        self.libraryid = libraryid
        self.update()
        self._n = 0

    def url(self):
        return utils.urls['libraries'] + '/' + self.libraryid 

    def url_docs(self):
        return utils.urls['documents'] + '/' + self.libraryid 

    def update(self):
        self.docs = []

        data = requests.get(
                            self.url(),
                            auth=utils.BearerAuth(self.token)
                        ).json()
        self.docs.extend(data['documents'])

        total_num = int(data['metadata']['num_documents'])
        if len(self.docs) < total_num:
            num_left = total_num - len(self.docs)
            data = requests.get(
                                self.url()+'?start='+str(len(self.docs))+'&rows='+str(num_left),
                                auth=utils.BearerAuth(self.token)
                            ).json()
            self.docs.extend(data['documents'])

        self.metadata = data['metadata']
        self.name = self.metadata['name']

    def keys(self):
        return self.docs

    @property
    def description(self):
        return self.metadata['description']

    def __getitem__(self,key):
        if key in self.docs:
            return articles.article(self.token,key)

    def __getattr__(self, key):
        if key in self.metadata.keys():
            return self.metadata[key]

    def __dir__(self):
        return self.metadata.keys() + ['keys','add','remove','get','update']

    def get(self, bibcode):
        return articles.article(self.token,bibcode=bibcode)

    def add(self, bibcode):
        '''
        Add bibcode to library
        '''
        data = {'bibcode':self._ensure_list(bibcode),"action":"add"}
        r = requests.post(
                            self.url_docs(),
                            auth=utils.BearerAuth(self.token),
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
                            auth=utils.BearerAuth(self.token),
                            headers={'Content-Type':'application/json'},
                            json = data
                        ).json()
        # Error check:
        if 'number_removed' not in r:
            raise ValueError(r['message'])

    def __len__(self):
        return len(self.docs)

    def __contains__(self, key):
        return key in self.docs

    def __iter__(self):
        return self

    def __next__(self):
        if self._n >= len(self.docs):
            raise StopIteration

        res = self.get(self.keys()[self._n])
        self._n +=1
        return res

    def reset(self):
        self._n = 0

    # Just makes sure we have a list of strings
    def _ensure_list(self, s):
        return s if isinstance(s, list) else list(s)
