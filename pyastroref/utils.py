# SPDX-License-Identifier: GPL-2.0-or-later

import os
import appdirs
import tempfile
import shutil
import urllib

import gi
gi.require_version('EvinceDocument', '3.0')
from gi.repository import EvinceDocument


if 'PYASTROREF_TEST' in os.environ:
    testing = True
else:
    testing = False
    
dir_store = appdirs.AppDirs("pyastroref")

def loc(filename):
    os.makedirs(dir_store.user_config_dir,exist_ok=True)
    return os.path.join(dir_store.user_config_dir,filename)

def read(filename):
    try:
        with open(filename,'r') as f:
            return f.readline().strip()
    except:
        return ''

def save(filename,data):
    try:
        with open(filename,'w') as f:
            f.write(data)
    except:
        pass

def pdf_save(folder):
    return save(loc('pdf_store'),folder)

def pdf_read():
    return read(loc('pdf_store'))
    
def ads_save(key):
    return save(loc('ads'),key)

def ads_read():
    return read(loc('ads'))

def orcid_save(key):
    return save(loc('orcid'),key)

def orcid_read():
    return read(loc('orcid'))


class file_downloader(object):
    def __init__(self,url):
        self.url = url
    
    def __enter__(self):
        self.out_file, self.filename = tempfile.mkstemp(suffix=b'')
        try:
            with urllib.request.urlopen(self.url) as response, open(self.filename,'wb') as f:
                shutil.copyfileobj(response, f)
                return self.filename
        except:
            return None

    def __exit__(self, type, value, tb):
        if tb is not None:
            os.remove(self.filename)

def download_file(url,filename):
    if os.path.exists(filename):
        return filename
    with file_downloader(url) as f:
        if f is None:
            return None
        shutil.move(f,filename)
    if os.path.exists(filename):
        # Test if actually a pdf:
        try:
            EvinceDocument.Document.factory_get_document('file://'+filename)
        except gi.repository.GLib.Error:
            print("Can't access ",str(filename))
            os.remove(filename)
            return None

        return filename