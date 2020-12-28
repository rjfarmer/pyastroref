import os
import re
import urllib

#import pyastroref.search.search as search
#import pyastroref.utils.utils as utils

# if utils.testing:
#     import ads.sandbox as ads
# else:
#     import ads


_fl_short =  ['bibcode','title','author','year']
_fl_full =   ['bibcode','title','author','year','abstract','reference',
                'citation','keyword','doi','pub','orcid_user',
                'page','identifier']
_fl_bibtex = ['bibcode','bibtex']
_year_start = '0000'
_year_end = '9999'

search_syntax = ["abs:","ack:","aff:","abstract:","alternate_bibcode:",
                "alternate_title:","arXiv:","arxiv_class:","author:",
                "bibcode:","bibgroup:","bibstem:","body:","copyright:",
                "data:","database:","pubtype:","doi:","full:","grant:",
                "identifier:","issue:","keyword:","lang:","object:",
                "orcid:","orcid_pub:","orcid_id:","orcid_other:",
                "page:","property:","read_count:","title:","vizier:",
                "volume:","year:"]


# Doi prefix https://gist.github.com/hubgit/5974663

    
# def parse_search(query):
#     if os.path.isfile(query):
#         print("Cant handle files yet")
#         return None
#     elif 'http://' in query or 'www.' in query or 'https://' in query:
#         return process_url(query)
#     elif any(i in query for i in search_syntax):
#         return query
#     x = query.split()
#     if len(x)==1:
#         return 'author:"'+x[0]+'"'
#     elif len(x)==2:
#         return 'author:"'+x[0]+'" '+' year:'+str(x[1])
  
# def process_url(query):
#     if 'adsabs.harvard.edu' in query: # ADSABS
#         q = query.split('/')
#         if len(q[-1])==19:
#             return 'bibcode:'+q[-1]
#         elif len(q[-2])==19:
#             return 'bibcode:'+q[-2]
#         else:
#             return None
#     elif 'arxiv.org/' in query: #ARIXV
#         return 'arXiv:'+query.split('/')[-1]
#     elif "iopscience.iop.org" in query: #ApJ, ApJS
#         #http://iopscience.iop.org/article/10.3847/1538-4365/227/2/22/meta
#         return 'doi:'+query.partition('article/')[-1].replace('/meta','')
#     elif 'academic.oup.com/mnras' in query: #MNRAS
#         # https://academic.oup.com/mnras/article/433/2/1133/1747991
#         d = re.sub("[a-zA-Z:]","",query).split('/')
#         doi = []
#         for i in d:
#             if len(i) and '..' not in i:
#                 doi.append(i)
#         return 'bibstem:mnras volume:'+doi[0]+' page:'+doi[2]
#     elif 'aanda.org' in query: #A&A:
#         #https://www.aanda.org/articles/aa/abs/2017/07/aa30698-17/aa30698-17.html
#         #Resort to downloading webpage as the url is useless
#         data = urllib.request.urlopen(query)
#         html = data.read()
#         ind = html.index(b'citation_bibcode')
#         x = html[ind:ind+50].decode()
#         #bibcdoes are 19 characters, but the & in A&A gets converted to %26
#         return 'bibcode:"'+str(x[27:27+21]).replace('%26','&')+'"'
#     elif 'nature.com' in query: #nature
#         #https://www.nature.com/articles/s41550-018-0442-z #plus junk after this
#         if '?' in query:
#             query = query[:query.index("?")]
#         data = urllib.request.urlopen(query+'.ris')
#         html = data.read().decode().split('\n')
#         for i in html:
#             if 'DO  -' in i:
#                 doi = i.split()[-1]
#                 return 'doi:'+i.split()[-1]
#     elif 'sciencemag.org' in query: #science
#         #http://science.sciencemag.org/content/305/5690/1582
#         data = urllib.request.urlopen(query)
#         html = data.read()
#         ind = html.index(b'citation_doi')
#         doi = html[ind:ind+100].decode().split('/>')[0].split('=')[-1].strip().replace('"','')
#         return "doi:" + doi
#     elif 'PhysRevLett' in query: #Phys Review Letter
#         #https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.116.241103
#         doi = '/'.join(query.split('/')[-2:])
#         return "doi:" + doi
        
#     return None
    

# class search(search.searcher):
#     def __init__(self,apikey=None):
#         self.ads = ads
#         if apikey is None:
#             apikey = load_apikey()
#         try:
#             self.ads.config.token = apikey
#         except AttributeError:
#             pass
        
#     def search_author_year(self,author,year,fields=_fl_full):
#         yr = self._parse_year_range(year)
#         a = self._parse_author(author)
#         query = a+' '+yr
#         yield self._process(self.ads.SearchQuery(q=query,fl=fields),fields)
        
#     def search_author(self,author,fields=_fl_full):
#         a = self._parse_author(author)
#         query = a
#         return self._process(self.ads.SearchQuery(q=query,fl=fields),fields)
        
#     def search(self,query,fields=_fl_full):
#         return self._process(self.ads.SearchQuery(q=query,fl=fields),fields)
        
#     def search_bibcode(self,bibcode,fields=_fl_full):
#         return self._process(list(self.ads.SearchQuery(bibcode=bibcode,fl=fields)),fields)

#     def get_all(self):
#         if utils.testing:
#             return self._process(list(self.ads.SearchQuery(author='me',fl=_fl_full)),_fl_full)
#         else:
#             print("Bad idea to return all possible papers with ads")


#     def _process(self,articles,fields):
#         for i in articles:
#             res = {}
#             for j in fields:
#                 res[j] = getattr(i,j)
#             yield res
        
#     def _parse_year_range(self,year=None):     
#         if year is None:
#             s,e = str(_year_start), str(_year_end)
#         elif str(year).endswith('-'):
#              s,e = str(year.replace('-','')), _year_end
#         elif str(year).startswith('-'):
#              s,e = _year_start,str(year.replace('-',''))
#         else:
#              s,e = str(year), str(year)
             
#         return 'pubdate:['+s+'-01 TO '+e+'-12]'
        
#     def _parse_author(self,author):
#         return 'author:("'+author+'")'
