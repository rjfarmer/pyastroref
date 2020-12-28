import os
import appdirs

if 'PYASTROREF_TEST' in os.environ:
    testing = True
else:
    testing = False
    
dir_store = appdirs.AppDirs("pyastroref")

def _store(filename):
    os.makedirs(dir_store.user_config_dir,exist_ok=True)
    return os.path.join(dir_store.user_config_dir,filename)

def _loc(filename):
    try:
        with open(filename,'r') as f:
            return f.readline().strip()
    except:
        return None

def pdf_store():
    return _store('pdf_store')

def pdf_loc():
    return _loc(pdf_store())
    
def db_store():
    return _store('db_store') 
    
def db_loc():
    return _loc(db_store())
