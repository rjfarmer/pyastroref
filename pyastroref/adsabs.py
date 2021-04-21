# SPDX-License-Identifier: GPL-2.0-or-later

import os
import re
import requests
import datetime
from pathlib import Path

import bibtexparser
from bibtexparser.bparser import BibTexParser
import feedparser
from appdirs import AppDirs

dirs = AppDirs("pyAstroRef")

os.makedirs(dirs.user_config_dir,exist_ok=True)


# Where to store ADS dev key, leave in ~/.ads to keep consistency with the ads package
_TOKEN_FILE = os.path.join(Path.home(),'.ads','dev_key')

# Where to store users ORCID key
_ORCID_FILE = os.path.join(dirs.user_config_dir,'orcid')

# Where to store PDF's
_PDFFOLDER_FILE = os.path.join(dirs.user_config_dir,'pdfs')

_base_url = 'https://api.adsabs.harvard.edu/v1/biblib'
_urls = {
    'base' :  _base_url,
    'libraries' : _base_url+'/libraries',
    'documents' :_base_url+'/documents',
    'permissions' :_base_url+'/permissionss',
    'transfer' :_base_url+'/transfer',
    'search': 'https://api.adsabs.harvard.edu/v1/search/query',
    'pdfs': 'https://ui.adsabs.harvard.edu/link_gateway/',
    'metrics': 'https://api.adsabs.harvard.edu/v1/metrics',
    'bibtex' : 'https://api.adsabs.harvard.edu/v1/export/bibtex'
}

# Default ADS search fields
_fields = ['bibcode','title','author','year','abstract','year',
            'pubdate','bibstem','alternate_bibcode','citation_count','identifier',
            'reference'
            ]

search_words = '''abs abstract ack aff aff_id alternate_bibcode alternative_title arXiv arxiv_class author author_count
                 bibcode bigroup bibstem body 
                 citation_count copyright 
                 data database pubdate doctype doi
                 full
                 grant
                 identifier inst issue 
                 keyword
                 lang
                 object orcid orcid_user orcid_other
                 page property
                 read_count
                 title
                 vizier volume
                 year
                '''.split()


# How many queries left today
_max_limit = 5000
_limit = 5000


# Handles setting the ADS dev token during a request call
# Use as requests.get(url,auth=_BearerAuth(ADS_TOKEN)
class _BearerAuth(requests.auth.AuthBase):
    def __init__(self, token):
        self.token = token
    def __call__(self, r):
        r.headers["authorization"] = "Bearer " + str(self.token)
        return r


class adsabs(object):
    def __init__(self):
        self._token = None
        self._orcid = None
        self._libs = None
        self._pdffolder = None 
        self.search_source = None

    @property
    def token(self):
        if self._token is None:
            try:
                with open(_TOKEN_FILE,'r') as f:
                    self._token = f.readline().strip() 
            except FileNotFoundError:
                return None
        return self._token

    @token.setter
    def token(self, token):
        self._token = token
        os.makedirs(os.path.basename(_TOKEN_FILE),exist_ok=True)
        with open(_TOKEN_FILE,'w') as f:
            print(self._token,file=f)
        

    @property
    def orcid(self):
        if self._orcid is None:
            try:
                with open(_ORCID_FILE,'r') as f:
                    self._orcid = f.readline().strip() 
            except FileNotFoundError:
                return None
        return self._orcid

    @orcid.setter
    def orcid(self, orcid):
        self._orcid = orcid
        os.makedirs(os.path.basename(_ORCID_FILE),exist_ok=True)
        with open(_ORCID_FILE,'w') as f:
            print(self._orcid,file=f)

    @property
    def pdffolder(self):
        if self._pdffolder is None:
            try:
                with open(_PDFFOLDER_FILE,'r') as f:
                    self._pdffolder = f.readline().strip() 
            except FileNotFoundError:
                return None
        return self._pdffolder

    @pdffolder.setter
    def pdffolder(self, pdffolder):
        self._pdffolder = pdffolder
        os.makedirs(os.path.basename(_PDFFOLDER_FILE),exist_ok=True)
        with open(_PDFFOLDER_FILE,'w') as f:
            print(self._pdffolder,file=f)

    def __getattr__(self, key):
        if key == 'libraries':
            if self._libs is None:
                self._libs  = libraries(self.token)
            return self._libs


    def article(self, bibcode):
        '''
        Returns an article given its bibcode
        '''
        return article(self.token,bibcode=bibcode)

    def search(self, query):
        '''
        Handles generic searching either via ads, bibtex, or passing a url

        Returns a jounral (list of articles)
        '''
        s = search(self.token)
        return s.search(query)


class libraries(object):
    '''
    This is a collection of ADS libraries that supports iteration
    '''
    def __init__(self, token):
        self.token = token
        self.data = None
        self._n = 0
        
    def update(self):
        data = requests.get(_urls['libraries'],
                            auth=_BearerAuth(self.token)
                            ).json()['libraries']
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
        r = requests.post(_urls['libraries'],
                auth=_BearerAuth(self.token),
                headers={'Content-Type':'application/json'},
                json = data).json()
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

        requests.delete(_urls['documents']+'/'+lid,
                auth=_BearerAuth(self.token)
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
        return _urls['libraries'] + '/' + self.libraryid 

    def url_docs(self):
        return _urls['documents'] + '/' + self.libraryid 

    def update(self):
        self.docs = []

        data = requests.get(self.url(),
                        auth=_BearerAuth(self.token)
                        ).json()
        self.docs.extend(data['documents'])

        total_num = int(data['metadata']['num_documents'])
        if len(self.docs) < total_num:
            num_left = total_num - len(self.docs)
            data = requests.get(self.url()+'?start='+str(len(self.docs))+'&rows='+str(num_left),
                            auth=_BearerAuth(self.token)
                            ).json()
            self.docs.extend(data['documents'])

        self.metadata = data['metadata']
        self.name = self.metadata['name']

    def keys(self):
        return self.docs

    def __getitem__(self,key):
        if key in self.docs:
            return article(self.token,key)

    def __getattr__(self, key):
        if key in self.metadata.keys():
            return self.metadata[key]

    def __dir__(self):
        return self.metadata.keys() + ['keys','add','remove','get','update']

    def get(self, bibcode):
        return article(self.token,bibcode=bibcode)

    def add(self, bibcode):
        '''
        Add bibcode to library
        '''
        data = {'bibcode':self._ensure_list(bibcode),"action":"add"}
        r = requests.post(self.url_docs(),
                auth=_BearerAuth(self.token),
                headers={'Content-Type':'application/json'},
                json = data).json()
        # Error check:
        if 'number_added' not in r:
            raise ValueError(r['message'])

    def remove(self, bibcode):
        '''
        Remove bibcode from library
        '''
        data = {'bibcode':self._ensure_list(bibcode),"action":"remove"}
        r = requests.post(self.url_docs(),
                auth=_BearerAuth(self.token),
                headers={'Content-Type':'application/json'},
                json = data).json()
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

class journal(object):
    '''
    This is a collection of articles that supports iterating over.

    We defer as much as possible actualy accessing data untill its needed
    '''
    def __init__(self, token, bibcodes, data=None):
        self.token = token
        self._set_bibcodes = set(bibcodes)   
        self._bibcodes = bibcodes    
        self._data = {}

        if data is not None:
            for i in data:
                self._data[i['bibcode']] = article(self.token, i['bibcode'], data=i)

        self._n = 0

    def __len__(self):
        return len(self._set_bibcodes)

    def __contains__(self, key):
        return key in self._set_bibcodes

    def __getitem__(self, key):
        if key in self._set_bibcodes:
            if key not in self._data:
                self._data[key] = article(self.token,bibcode=key)
            return self._data[key]
        else:
            return self.__getitem__(self._bibcodes[key])

    def __iter__(self):
        return self

    def __next__(self):
        if self._n >= len(self._bibcodes):
            raise StopIteration

        res = self.__getitem__(self._bibcodes[self._n])
        self._n +=1
        return res

    def reset(self):
        self._n = 0

    def keys(self):
        return self._set_bibcodes

    def bibcodes(self):
        return self.keys()


class article(object):
    '''
    A single article that is given by either a bibcode, arxic id, or doi.
    Bibcodes are allways the prefered ID as the doi or arxiv id we query  ADS for its bibcode.

    We defer actually searching the ads untill the user asks for a field.
    Thus we can make as many article as we want (if we allready know the bibcode)
    without hitting the ADS api limits.
    '''

    def __init__(self, token, bibcode=None, data=None):
        self.token = token
        self._bibcode = bibcode
        self._data = None
        self._citations=None
        self._references=None
        self.which_file=None

        if data is not None:
            self._data = data
            self._bibcode = self._data['bibcode']
    
    def search(self,force=False):
        if self._data is None or force:
            self._data = search(self.token).bibcode_single(self.bibcode)
            
    @property
    def bibcode(self):
        return self._bibcode

    def __gettattr__(self, key):
        if self._data is not None:
            if key in self._data:
                return self._data[key]

    @property
    def title(self):
        if self._data is None:
            self.search()
        return self._data['title'][0]

    @property
    def authors(self):
        if self._data is None:
            self.search()
        return  '; '.join(self._data['author'])

    @property
    def first_author(self):
        if self._data is None:
            self.search()
        return self._data['author'][0]

    @property
    def pubdate(self):
        if self._data is None:
            self.search()
        return self._data['pubdate']

    @property
    def journal(self):
        if self._data is None:
            self.search()
        return self._data['bibstem'][0]

    def filename(self, full=False):
        if full:
            return os.path.join(adsabs().pdffolder,self.bibcode+'.pdf')
        else:
            return self.bibcode+'.pdf'

    @property
    def year(self):
        if self._data is None:
            self.search()
        return self._data['year']

    @property
    def abstract(self):
        if self._data is None:
            self.search()
        return self._data['abstract']

    @property
    def name(self):
        if self._data is None:
            self.search()
        return self.first_author + ' ' + self.year

    @property
    def ads_url(self):
        if self._data is None:
            self.search()
        return 'https://ui.adsabs.harvard.edu/abs/'+self.bibcode

    @property
    def arxiv_url(self):
        if self._data is None:
            self.search()
        arxiv_id = None
        for i in self._data['identifier']:
            if i.startswith('arXiv:'):
                arxiv_id = i.replace('arXiv:','')

        if arxiv_id is not None:
            return 'https://arxiv.org/abs/'+arxiv_id
        else:
            return ''

    @property
    def journal_url(self):
        if self._data is None:
            self.search()
        doi = None
        for i in self._data['identifier']:
            if i.startswith('10.'):
                doi = i
        if doi is not None:
            return  'https://doi.org/'+doi
        else:
            return ''

    @property
    def citation_count(self):
        if self._data is None:
            self.search()
        return self._data['citation_count']

    @property
    def reference_count(self):
        if self._data is None:
            self.search()
        if 'reference' not in self._data:
            return 0
        else:
            return len(self._data['reference'])
    
    def pdf(self, filename):
        # There are multiple possible locations for the pdf
        # Try to avoid the journal links as that usally needs a 
        # vpn working to use a university ip address
        strs = ['/PUB_PDF','/EPRINT_PDF','/ADS_PDF']

        if os.path.exists(filename):
            return

        for i in strs:
            url = _urls['pdfs']+str(self.bibcode)+i

            # Pretend to be Firefox otherwise we hit captchas
            headers = {'user-agent': 'Mozilla /5.0 (Windows NT 10.0; Win64; x64)'}
            try:
                r = requests.get(url, allow_redirects=True,headers=headers)
            except:
                raise ValueError("Couldn't download file")

            if r.content.startswith(b'<!DOCTYPE html'): 
                continue

            with open(filename,'wb') as f:
                f.write(r.content)
                self.which_file = i
                break

        if not os.path.exists(filename):
            raise ValueError("Couldn't download file")

    def citations(self):
        if self._citations is None:
            self._citations = search(self.token).search('citations(bibcode:"'+self._bibcode+'")')
        return self._citations

    def references(self):
        if self._references is None:
            self._references = search(self.token).search('references(bibcode:"'+self._bibcode+'")')
        return self._references 

    def bibtex(self,filename=None,text=True):
        data = {'bibcode':[self.bibcode]}
        r = requests.post(_urls['bibtex'],
                auth=_BearerAuth(self.token),
                headers={'Content-Type':'application/json'},
                json = data).json()

        if 'error' in r:
            raise ValueError(r['error'])

        if filename is not None:
            with open(filename,'w') as f:
                f.write(r['export'])

        if text:
            return r['export']
        else:
            bp = BibTexParser(interpolate_strings=False)
            return bibtexparser.loads(r['export'],parser=bp)

    def __str__(self):
        return self.name

    def __reduce__(self):
        return (article, (self.token,self.bibcode))
    

class search(object):
    def __init__(self, token):
        self.token = token

    def search(self, query):
        # Check if url?
        
        for func in [self._process_url,self._process_bibtex]:
            res = func(query)
            if len(res):
                query = self.make_query(res)
                break
        
        print(query)
        bibs, data = self._query(query)
        return journal(self.token,bibs,data=data)

    def make_query(self, identifer):
        q=''
        if 'bibcode' in identifer:
            q = 'bibcode:'+identifer['bibcode']
        elif 'arxiv' in identifer:
            q = 'arxiv:'+identifer['arxiv']
        elif 'doi' in identifer:
            q = 'doi:'+identifer['doi']

        return q

    def _process_bibtex(self, query):
        res = {}
        if query.startswith('@'):
            bp = BibTexParser(interpolate_strings=False)
            bib = bibtexparser.loads(query,filter=bp)
            bib = bib.entries[0]
            #What is in the bib?
            if 'adsurl' in bib:
                res['bibcode'] = bib['adsurl'].split('/')[-1]
            elif 'eprint' in bib:
                res['arxiv'] = bib['eprint']
            elif 'doi' in bib:
                res['doi'] = bib['doi']
            else:
                raise ValueError("Don't understand this bitex")
        return res


    def _query(self, query):

        start = 0
        results = []
        while True:
            r = self._query_ads(query,start)

            # Did we get everything?
            data = r.json()
            results.extend(data['response']['docs'])
            num_found = int(data['response']['numFound'])
            num_got = len(results)

            if num_got >= num_found:
                break

            start = len(results)

        bibcodes = [i['bibcode'] for i in results]

        return bibcodes, results

    def _query_ads(self, query, start=0):
        r = requests.get(_urls['search'],
                            auth=_BearerAuth(self.token),
                            params={
                                'q':query,
                                'fl':_fields,
                                'rows':100,
                                'start':start
                            }
                        )
        # Get rate limits
        try:
            _limit = int(r.headers['X-RateLimit-Remaining'])
            _max_limit = int(r.headers['X-RateLimit-Limit'])
        except KeyError:
            pass

        return r


    def bibcode_single(self, bibcode):
        return self.search('bibcode:"'+str(bibcode) +'"')


    def bibcode_multi(self, bibcodes):
        return self.chunked_search(bibcodes,'bibcode:')

    def arxiv_multi(self, arxivids):
        return self.chunked_search(arxivids,'identifier:')


    def orcid(self, orcid):
        return self.search('orcid:"'+str(orcid) +'"')

    def first_author(self, author):
        return self.search('author:"^'+author+'"')


    def _process_url(self, url):
        '''
        Given an URL attempts to work out the bibcode, arxiv id, or doi for it
        '''

        res = {}
        headers = {'user-agent': 'Mozilla /5.0 (Windows NT 10.0; Win64; x64)'}

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
            r=requests.get(url,headers=headers)
            for i in r.text.split():
                if 'doi.org' in i and '>' in i:
                    break # Many matches but we want the line which has a href=url>
            res['doi'] = i.split('>')[1].split('<')[0].split('doi.org/')[1]
        elif 'aanda.org' in url: #A&A:
            #https://www.aanda.org/articles/aa/abs/2017/07/aa30698-17/aa30698-17.html
            #Resort to downloading webpage as the url is useless
            r=requests.get(url,headers=headers)
            for line in r.text.split('>'):
                if 'citation_bibcode' in line:
                    #bibcodes are 19 characters, but the & in A&A gets converted to %26
                    res['bibcode'] = line.split('=')[-1].replace('%26','&')
                    break
        elif 'nature.com' in url: #nature
            #https://www.nature.com/articles/s41550-018-0442-z #plus junk after this
            if '?' in url:
                url = url[:url.index("?")]
            r=requests.get(url+'.ris',headers=headers)
            for i in r.text.split():
                if 'doi.org' in i:
                    res['doi'] = '/'.join(i.split('/')[-2:])
                    break
        elif 'sciencemag.org' in url: #science
            #http://science.sciencemag.org/content/305/5690/1582
            r=requests.get(url,headers=headers)
            for line in r.text.split('>'):
                if 'meta name="citation_doi"' in line:
                    res['doi'] = line.split('=')[-1].replace('"','').removesuffix('/').strip()
        elif 'PhysRevLett' in url: #Phys Review Letter
            #https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.116.241103
            doi = '/'.join(url.split('/')[-2:])
            res['doi'] = doi
        
        return res


    def chunked_search(self, ids, prefix):
        # Break up data into chunks to process otherwise we max at 50 entries:
        query = self.chunked_join(ids,prefix=prefix,joiner=' OR ')
        alldata = []
        allbibs=[]
        for i in query:
            bibs, data = self._query(i)
            alldata.extend(data)
            allbibs.extend(bibs)

        return journal(self.token,bibcodes=allbibs,data=alldata)


    def chunked_join(self, data,prefix='',joiner='',nmax=20):
        '''
        Breaks data into chunks of maximum size nmax

        Each element of the chunked data is prefixed with prefix and joined back together with joiner

        data = ['1','2','3','4']
        _chunked_join(data,prefix='bibcode:','joiner=' OR ',nmax=2)

        ['bibcode:1 OR bibcode:2','bibcode:3 OR bibcode:4']

        Handy to break up large queries that might exceed search limits (seems to be a max of 50
        bibcodes or arxiv ids at a time).
        Where prefix is the ads term ('bibcode:' or 'indentifier:')
        and joiner is logical or ' OR '

        '''
        res = []

        for pos in range(0, len(data), nmax):
            x = [prefix+j for j in data[pos:pos + nmax]]
            res.append(joiner.join(x))

        return res



class arxivrss(object):
    def __init__(self, token):
        self.url = 'http://export.arxiv.org/rss/astro-ph'
        self._feed = None
        self.token = token
        self._data = []

    def articles(self):
        if self._feed is None:
            self._feed = feedparser.parse(self.url)
            arxiv_ids = [i['id'].split('/')[-1] for i in self._feed['entries']]

            # Filter resubmissions out
            today=datetime.date.today()
            thismonth = str(today.year-2000)+str(today.month).zfill(2)
            arxiv_ids = [i for i in arxiv_ids if i.startswith(thismonth)]

            self._data = search(self.token).arxiv_multi(arxiv_ids)

        return self._data


class JournalData(object):
    _url = 'http://adsabs.harvard.edu/abs_doc/journals1.html'

    default_journals = {
        'Astronomy and Astrophysics':'A&A',
        'The Astrophysical Journal':'ApJ',
        'The Astrophysical Journal Supplement Series':'ApJS',
        'Monthly Notices of the Royal Astronomical Society':'MNRAS',
        'Nature':'Natur',
        'Nature Astronomy':'NatAs',
        'Science':'Sci'
    }

    _file = Path(os.path.join(dirs.user_config_dir,'all_journals'))

    def __init__(self, token):
        self.token = token
        self._data = {}
        self._results = {}
        self.update_journals()

    def if_update_journal(self):
        if not os.path.exists(self._file):
            return True

        last_week = datetime.date.today() - datetime.timedelta(days=7)
        last_modified = datetime.date.fromtimestamp(self._file.stat().st_mtime)
        if last_modified < last_week:
            return True

        return False

    def update_journals(self):
        if self.if_update_journal():
            self.make_file()

        self.read_file()


    def make_file(self):
        r = requests.get(self._url)
        data = r.content.decode().split('\n')
        
        res = {}
        for line in data:
            if line.startswith('<a href="#" onClick='):
                _, journ_short, name = line.split('>')
                journ_short = journ_short.split()[0].strip()
                name = name.strip()
                res[name] = journ_short

        with open(self._file,'w') as f:
            for key,value in res.items():
                print(key,value,file=f)

    def read_file(self):
        self._data = {}
        with open(self._file,'r') as f:
            for line in f.readlines():
                l = line.split()
                value = l[-1]
                key = ' '.join(l[:-1])
                self._data[key.strip()] = value.strip()

        # Remove default journals
        for k in self.default_journals.keys():
            self._data.pop(k, None)

    def list_defaults(self):
        return self.default_journals.keys()

    def list_all(self):
        return self._data.keys()

    def search(self, name):
        for key,value in self.default_journals.items():
            if value == name:
                break

        if name not in self._results:
            today = datetime.date.today()
            monthago = today - datetime.timedelta(days=31)

            pubdata = "pubdate:["
            pubdata+= str(monthago.year) +"-"+ str(monthago.month).zfill(2)
            pubdata+= ' TO '
            pubdata+= str(today.year) +"-"+ str(today.month).zfill(2)
            pubdata+=']'

            query = 'bibstem:"'+name+'" AND '+pubdata

            self._results[name] = search(self.token).search(query)

        self._results[name].reset()
        return self._results[name]
