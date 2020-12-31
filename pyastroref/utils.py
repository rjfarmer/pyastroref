# SPDX-License-Identifier: GPL-2.0-or-later

import os
import appdirs
import tempfile
import shutil
import urllib
import requests

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
    if os.path.exists(filename):
        return filename
    
    headers = {'user-agent': 'my-app/0.0.1'}
    r = requests.get(url, allow_redirects=True,headers=headers)
    with open(filename,'wb') as f:
        f.write(r.content)
    
    if os.path.exists(filename):
        # Test if actually a pdf:
        try:
            EvinceDocument.Document.factory_get_document('file://'+filename)
        except gi.repository.GLib.Error:
            print("Not a pdf ",str(filename))
            os.remove(filename)
            return None

        return filename

def process_url(url):
    res = {}

    if 'adsabs.harvard.edu' in url: # ADSABS
        q = url.split('/')
        if len(q[-1])==19:
            res['bibcode'] = q[-1]
        elif len(q[-2])==19:
            res['bibcode'] = q[-2]
        else:
            res['bibcode'] = None
    elif 'arxiv.org/' in url: #ARXIV
        res['arxiv'] = url.split('/')[-1]
    elif "iopscience.iop.org" in url: #ApJ, ApJS
        #http://iopscience.iop.org/article/10.3847/1538-4365/227/2/22/meta
        res['doi'] = url.partition('article/')[-1].replace('/meta','')
    elif 'academic.oup.com/mnras' in url: #MNRAS
        # https://academic.oup.com/mnras/article/433/2/1133/1747991
        # Fake some headers
        headers = {'user-agent': 'my-app/0.0.1'}
        r=requests.get(url,headers=headers)
        for i in r.text.split():
            if 'doi.org' in i and '>' in i:
                break # Many matches but we want the line which has a href=url>
        res['doi'] = i.split('>')[1].split('<')[0].split('doi.org/')[1]
    elif 'aanda.org' in url: #A&A:
        #https://www.aanda.org/articles/aa/abs/2017/07/aa30698-17/aa30698-17.html
        #Resort to downloading webpage as the url is useless
        data = urllib.request.urlopen(url)
        html = data.read()
        ind = html.index(b'citation_bibcode')
        x = html[ind:ind+50].decode()
        #bibcodes are 19 characters, but the & in A&A gets converted to %26
        res['bibcode'] = str(x[27:27+21]).replace('%26','&')
    elif 'nature.com' in url: #nature
        #https://www.nature.com/articles/s41550-018-0442-z #plus junk after this
        if '?' in url:
            url = url[:url.index("?")]
        data = urllib.request.urlopen(url+'.ris')
        html = data.read().decode().split('\n')
        for i in html:
            if 'DO  -' in i:
                doi = i.split()[-1]
                res['doi'] = i.split()[-1]
                break
    elif 'sciencemag.org' in url: #science
        #http://science.sciencemag.org/content/305/5690/1582
        data = urllib.request.urlopen(url)
        html = data.read()
        ind = html.index(b'citation_doi')
        doi = html[ind:ind+100].decode().split('/>')[0].split('=')[-1].strip().replace('"','')
        res['doi'] = doi
    elif 'PhysRevLett' in url: #Phys Review Letter
        #https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.116.241103
        doi = '/'.join(url.split('/')[-2:])
        res['doi'] = doi
        
    return res