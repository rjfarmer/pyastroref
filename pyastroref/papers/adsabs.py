# SPDX-License-Identifier: GPL-2.0-or-later

import os
import re
import requests
import datetime
from pathlib import Path


from . import utils
from . import articles
from . import libraries

# How many queries left today
_max_limit = 5000
_limit = 5000


class adsabs(object):
    def __init__(self):
        self._token = None
        self._orcid = None
        self._libs = None
        self._pdffolder = None 
        self.search_source = None
        self.settings = utils.settings

    @property
    def token(self):
        if self._token is None:
            self._token = utils.read_key_file(self.settings['TOKEN_FILE'])
        return self._token

    @token.setter
    def token(self, token):
        self._token = token
        utils.save_key_file(self.settings['TOKEN_FILE'],self._token)
        

    @property
    def orcid(self):
        if self._orcid is None:
            self._orcid = utils.read_key_file(self.settings['ORCID_FILE'])
        return self._orcid

    @orcid.setter
    def orcid(self, orcid):
        self._orcid = orcid
        utils.save_key_file(self.settings['ORCID_FILE'],self._orcid)

    @property
    def pdffolder(self):
        if self._pdffolder is None:
            self._pdffolder = utils.read_key_file(self.settings['PDFFOLDER_FILE'])
        return self._pdffolder

    @pdffolder.setter
    def pdffolder(self, pdffolder):
        self._pdffolder = pdffolder
        utils.save_key_file(self.settings['PDFFOLDER_FILE'],self._pdffolder)

    def __getattr__(self, key):
        if key == 'libraries':
            if self._libs is None:
                self._libs  = libraries.libraries(self.token)
            return self._libs


    def article(self, bibcode):
        '''
        Returns an article given its bibcode
        '''
        return articles.article(self.token,bibcode=bibcode)

    def search(self, query):
        '''
        Handles generic searching either via ads, bibtex, or passing a url

        Returns a journal (list of articles)
        '''
        s = articles.search(self.token)
        return s.search(query)

