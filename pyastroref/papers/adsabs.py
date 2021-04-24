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
        self._libs = None
        self.search_source = None
        self.settings = utils.settings

    def reload(self):
        self._libs = None
        self.search_source = None

    @property
    def token(self):
        return utils.read_key_file(self.settings['TOKEN_FILE'])

    @token.setter
    def token(self, token):
        utils.save_key_file(self.settings['TOKEN_FILE'],token)
        
    @property
    def orcid(self):
        return utils.read_key_file(self.settings['ORCID_FILE'])

    @orcid.setter
    def orcid(self, orcid):
        utils.save_key_file(self.settings['ORCID_FILE'],orcid)

    @property
    def pdffolder(self):
        return utils.read_key_file(self.settings['PDFFOLDER_FILE'])

    @pdffolder.setter
    def pdffolder(self, pdffolder):
        utils.save_key_file(self.settings['PDFFOLDER_FILE'],pdffolder)

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

