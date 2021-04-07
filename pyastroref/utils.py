# SPDX-License-Identifier: GPL-2.0-or-later

import os
import appdirs
import tempfile
import shutil
import requests
import threading
from pathlib import Path

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

def db_read():
    return read(loc('pdf_store')) # Store db in same folder as pdf's



def download_file(url,filename):
    def download():
        headers = {'user-agent': 'my-app/0.0.1'}
        r = requests.get(url, allow_redirects=True,headers=headers)
        with open(filename,'wb') as f:
            f.write(r.content)

    if os.path.exists(filename):
        return filename
    
    thread = threading.Thread(target=download)
    thread.daemon = True
    thread.start()
    
    if os.path.exists(filename):
        # Test if actually a pdf:
        try:
            EvinceDocument.Document.factory_get_document(path(filename).as_uri())
        except gi.repository.GLib.Error:
            print("Not a pdf ",str(filename))
            os.remove(filename)
            return None

        return filename

