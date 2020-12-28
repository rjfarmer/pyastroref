import os
import appdirs

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