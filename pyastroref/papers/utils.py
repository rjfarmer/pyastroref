# SPDX-License-Identifier: GPL-2.0-or-later

import os
import re
import requests
import datetime
from pathlib import Path
from appdirs import AppDirs

dirs = AppDirs("pyAstroRef")

os.makedirs(dirs.user_config_dir,exist_ok=True)

settings = {
    # Where to store ADS dev key, leave in ~/.ads to keep consistency with the ads package
    'TOKEN_FILE':os.path.join(Path.home(),'.ads','dev_key'),
    # Where to store users ORCID key
    'ORCID_FILE':os.path.join(dirs.user_config_dir,'orcid'),
    # Where to store PDF's
    'PDFFOLDER_FILE': os.path.join(dirs.user_config_dir,'pdfs'),
    # Where to store list of journals
    'ALL_JOURNALS_LIST':os.path.join(dirs.user_config_dir,'all_journals'),
    # Where to store list of to display
    'JOURNALS_LIST':os.path.join(dirs.user_config_dir,'journals'),
}


urls = {
    'base' :  'https://api.adsabs.harvard.edu/v1/biblib',
    'libraries' : 'https://api.adsabs.harvard.edu/v1/biblib/libraries',
    'documents' :'https://api.adsabs.harvard.edu/v1/biblib/documents',
    'permissions' :'https://api.adsabs.harvard.edu/v1/biblib/permissionss',
    'transfer' :'https://api.adsabs.harvard.edu/v1/biblib/transfer',
    'search': 'https://api.adsabs.harvard.edu/v1/search/query',
    'pdfs': 'https://ui.adsabs.harvard.edu/link_gateway/',
    'metrics': 'https://api.adsabs.harvard.edu/v1/metrics',
    'bibtex' : 'https://api.adsabs.harvard.edu/v1/export/bibtex'
}


def save_key_file(filename,key):
    os.makedirs(os.path.basename(filename),exist_ok=True)
    with open(filename,'w') as f:
        print(key,file=f)

def read_key_file(filename):
    try:
        with open(filename,'r') as f:
            result = f.readline().strip() 
    except FileNotFoundError:
        return None
    return result


# Handles setting the ADS dev token during a request call
# Use as requests.get(url,auth=_BearerAuth(ADS_TOKEN)
class BearerAuth(requests.auth.AuthBase):
    def __init__(self, token):
        self.token = token
    def __call__(self, r):
        r.headers["authorization"] = "Bearer " + str(self.token)
        return r
