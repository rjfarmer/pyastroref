import tempfile
import urllib
import os
import shutil

import pyastroref.utils.utils as utils

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

            
            
class download(object):
    def __init__(self, bibcode,identifers):
        self.identifers = identifers
        self.bibcode = bibcode
        
    def find_doi(self):
        self.doi = None
        for i in self.identifers:
            if '/' in i:
                self.doi = i
                break
                
    def find_arixv(self):
        self.arixv = None
        for i in self.identifers:
            try:
                self.arixv = str(float(i)) # Arixv identifers are the only one thats a number
            except ValueError: 
                pass
            
    def save_name(self):
        with open(utils.pdf_store(),'r') as f:
            folder = f.readline().strip()
        return os.path.join(folder,self.bibcode+'.pdf')
        
    def download_arxiv(self):
        fileout = self.save_name()
        if os.path.isfile(fileout):
            return fileout
            
        if self.arixv is not None:
            url = 'https://arxiv.org/pdf/'+str(self.arixv)
            filename = self.download_file(url)
            shutil.move(filename,fileout)
            return fileout
        else:
            return None
            
    def download(self):
        fileout = self.save_name()
        if os.path.isfile(fileout):
            return fileout
        url = 'https://ui.adsabs.harvard.edu/link_gateway/'+str(self.bibcode)+'/PUB_PDF'
        filename = self.download_file(url)
        if filename is None:
            url = 'https://ui.adsabs.harvard.edu/link_gateway/'+str(self.bibcode)+'/EPRINT_PDF'
            filename = self.download_file(url)
        if filename is None:
            url = 'https://ui.adsabs.harvard.edu/link_gateway/'+str(self.bibcode)+'/ADS_PDF'
            filename = self.download_file(url)
        
        shutil.move(filename,fileout)
        return fileout  
        


    def download_file(self,url):
        with file_downloader(url) as filename:
            return filename
