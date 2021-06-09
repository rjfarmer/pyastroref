# SPDX-License-Identifier: GPL-2.0-or-later

import os
import re
import requests
import datetime
from pathlib import Path

import bibtexparser
from bibtexparser.bparser import BibTexParser

from . import utils


# Default ADS search fields
_fields = ['bibcode','title','author','year','abstract',
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



class journal(object):
    '''
    This is a collection of articles that supports iterating over.

    We defer as much as possible actualy accessing data untill its needed
    '''
    def __init__(self, adsdata, bibcodes, data=None):
        self.adsdata = adsdata
        self._set_bibcodes = set(bibcodes)   
        self._bibcodes = bibcodes    
        self._data = {}

        if data is not None:
            for i in data:
                self._data[i['bibcode']] = article(self.adsdata, i['bibcode'], data=i)

    def __len__(self):
        return len(self._set_bibcodes)

    def __contains__(self, key):
        return key in self._set_bibcodes

    def __getitem__(self, key):
        if key in self._set_bibcodes:
            if key not in self._data:
                self._data[key] = article(self.adsdata,bibcode=key)
            return self._data[key]
        else:
            return self.__getitem__(self._bibcodes[key])

    def __iter__(self):
        for i in self._bibcodes:
            yield self.__getitem__(i)

    def keys(self):
        return self._set_bibcodes

    def bibcodes(self):
        return self.keys()

    def values(self):
        return self._data.values()

    def items(self):
        return self._data.items()


class article(object):
    '''
    A single article that is given by either a bibcode, arxic id, or doi.
    Bibcodes are allways the prefered ID as the doi or arxiv id we query  ADS for its bibcode.

    We defer actually searching the ads untill the user asks for a field.
    Thus we can make as many article as we want (if we allready know the bibcode)
    without hitting the ADS api limits.
    '''

    def __init__(self, adsdata, bibcode=None, data=None):
        self.adsdata = adsdata
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
            self._data = self.adsdata.search.bibcode_single(self.bibcode)
            
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
            return os.path.join(utils.read_key_file(utils.settings['PDFFOLDER_FILE']),
                                self.bibcode+'.pdf')
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
        if 'abstract' in self._data:
            return self._data['abstract']
        else:
            return ''

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
        if 'citation_count' not in self._data:
            return 0
        else:
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

        got_file=False
        for i in strs:
            url = utils.urls['pdfs']+str(self.bibcode)+i

            # Pretend to be Firefox otherwise we hit captchas
            headers = {'user-agent': 'Mozilla /5.0 (Windows NT 10.0; Win64; x64)'}
            try:
                r = requests.get(url, allow_redirects=True,headers=headers)
            except:
                continue

            if r.content.startswith(b'<!DOCTYPE html'): 
                continue

            with open(filename,'wb') as f:
                f.write(r.content)
                self.which_file = i
                got_file=True
                break

        if not os.path.exists(filename):
            raise utils.FileDonwnloadFailed("Couldn't download file")

    def citations(self):
        if self._citations is None:
            self._citations = self.adsdata.search('citations(bibcode:"'+self._bibcode+'")')
        return self._citations

    def references(self):
        if self._references is None:
            self._references = self.adsdata.search('references(bibcode:"'+self._bibcode+'")')
        return self._references 

    def bibtex(self):
        data = {'bibcode':[self.bibcode]}
        r = requests.post(utils.urls['bibtex'],
                auth=utils.BearerAuth(self.adsdata.token),
                headers={'Content-Type':'application/json'},
                json = data).json()

        if 'error' in r:
            raise ValueError(r['error'])

        return r['export']

    def __str__(self):
        return self.name

    def __reduce__(self):
        return (article, (self.adsdata,self.bibcode))

    def __hash__(self):
        return hash(self.bibcode)

    def __eq__(self, value):
        if isinstance(value, article):
            if value.bibcode == self.bibcode:
                return True
        return False


class search(object):
    def __init__(self, adsdata):
        self.adsdata = adsdata

    def search(self, query):
        if not len(query):
            return []

        # Check if url?
        for func in [self._process_url,self._process_bibtex]:
            res = func(query)
            if len(res):
                query = self.make_query(res)
                break
        
        print(query)
        bibs, data = self._query(query)
        return journal(self.adsdata,bibs,data=data)

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


    def _query(self, query, max_rows=250):

        start = 0
        results = []
        while True:
            r = self._query_ads(query,start)

            # Did we get everything?
            data = r.json()

            if 'response' not in data:
                raise SearchError()

            results.extend(data['response']['docs'])
            num_found = int(data['response']['numFound'])
            num_got = len(results)

            if num_got >= num_found:
                break

            if num_got > max_rows:
                break

            start = num_got

        bibcodes = [i['bibcode'] for i in results]

        return bibcodes, results

    def _query_ads(self, query, start=0):
        r = requests.get(
                        utils.urls['search'],
                        auth=utils.BearerAuth(self.adsdata.token),
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
            res['arxiv'] = url.split('/')[-1].split('v')[0]
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

        return journal(self.adsdata,bibcodes=allbibs,data=alldata)


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


class SearchError(Exception):
    pass