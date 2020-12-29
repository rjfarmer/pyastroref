# SPDX-License-Identifier: GPL-2.0-or-later

import threading
import time
import os
import tempfile
import urllib
import shutil
import feedparser
import requests
import ads

from . import utils

import gi
gi.require_version("Gtk", "3.0")
gi.require_version('EvinceDocument', '3.0')
gi.require_version('EvinceView', '3.0')
from gi.repository import GLib, Gtk, GObject, Gio
from gi.repository import EvinceDocument
from gi.repository import EvinceView


EvinceDocument.init()

_pages = {}

class MyWindow(Gtk.Window):
    def __init__(self):
        self.settings = {}
        self.pages = {}

        Gtk.Window.__init__(self, title="pyAstroRef")

        self.setup_headerbar()
        self.setup_search_bar()
        self.setup_notebook()
        self.setup_grid()       

        t = utils.ads_read()
        if t is None or len(t)==0:
            self.warn_ads_not_set()

    def on_click_load_options(self, button):
        win = OptionsMenu()
        win.show_all()

    def on_click_search(self, button):
        query = self.search.get_text()

        if len(query) == 0:
            return

        Search(self.notebook, query)

    def setup_search_bar(self):
        self.search = Gtk.SearchEntry()
        self.search.set_width_chars(100)
        self.search.connect("activate",self.on_click_search)

        self.search.set_can_default(True)
        self.set_default(self.search)
        self.search.set_hexpand(True)

    def setup_headerbar(self):
        self.button_opt = Gtk.Button()
        self.button_opt.connect("clicked", self.on_click_load_options)
        image = Gtk.Image()
        image.set_from_icon_name('open-menu-symbolic', Gtk.IconSize.BUTTON)
        self.button_opt.set_image(image)

        hb = Gtk.HeaderBar()
        hb.set_show_close_button(True)
        hb.props.title = "pyAstroRef"
        self.set_titlebar(hb)

        hb.pack_start(self.button_opt)

    def setup_notebook(self):
        self.notebook = Gtk.Notebook()
        self.notebook.set_hexpand(True)
        self.notebook.set_vexpand(True)
        self.notebook.set_tab_pos(Gtk.PositionType.LEFT)
        
    def setup_grid(self):
        self.grid = Gtk.Grid()
        self.add(self.grid)

        self.grid.add(self.search)
        self.grid.attach_next_to(self.notebook,self.search,
                             Gtk.PositionType.BOTTOM,1,1) 


    def warn_ads_not_set(self):
        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text="ADSABS Key not set",
        )
        dialog.format_secondary_markup(
            'Please visit '
        '<a href="https://ui.adsabs.harvard.edu/user/settings/token"'
        'title="Click here">'
        'https://ui.adsabs.harvard.edu/user/settings/token</a>'
        ' and set a token inside the options menu'
        )
        dialog.run()

        dialog.destroy()

class Search(object):
    def __init__(self, notebook, query):
        self.query = query
        self.notebook = notebook

        #self.new_pdf_page(query)
        self.new_search_page(query)

    def new_pdf_page(self,filename):
        self.new_page(pdfPage,os.path.join(utils.pdf_read(),self.query+'.pdf'))

    def new_search_page(self, query):
        def search():
            self.new_page(searchPage,query)

        thread = threading.Thread(target=search)
        thread.daemon = True
        thread.start()

    def new_page(self,ptype,name):
        if name in _pages:
            if _pages[name].page_num >= 0:
                self.notebook.set_current_page(_pages[name].page_num)
                return
        
        _pages[name] = ptype(self.notebook, name)
        self.add_to_notebook(_pages[name])        

    def add_to_notebook(self, page):
        index = self.notebook.append_page(page.add_page(),page.make_header())
        page.page_num = index
        self.notebook.set_tab_reorderable(page.page, True)
        self.notebook.show_all()
        self.notebook.set_current_page(page.page_num)  


class downloadGeneric(object):

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

    def download_file(self,url,filename):
        if os.path.exists(filename):
            return filename
        with self.file_downloader(url) as f:
            if f is None:
                return None
            shutil.move(f,filename)
        if os.path.exists(filename):
            return filename

class downloadADS(downloadGeneric):
    _fields = ['bibcode','title','author','year','abstract',
                        'pubdate']
    _search_url = 'https://ui.adsabs.harvard.edu/link_gateway/'

    def __init__(self,bibcode=None,ident=None):
        ads.config.token = utils.ads_read()
        
        self.bibcode = bibcode
        self.ident = ident

        if self.bibcode is not None:
            self.get_data()
        if self.ident is not None:
            self.get_bibcode()
    
    def get_data(self):
        self.data = list(ads.SearchQuery(bibcode=self.bibcode,
                    fl=self._fields))[0]

    def get_bibcode(self):
        if 'bibcode' in self.ident:
            self.bibcode = self.ident['bibcode']
            self.get_data()
            return

        if 'doi' in self.ident:
            self.data = list(ads.SearchQuery(doi=self.ident['doi'],fl=self._fields))[0]
        elif 'arxiv' in self.ident:
            self.data = list(ads.SearchQuery(q=self.ident['arxiv'],fl=self._fields))[0]
        else:
            raise ValueError("Didnt match ident, got",self.ident)

        self.bibcode = self.data.bibcode

    def title(self):
        return self.data.title

    def authors(self):
        return self.data.author

    def first_author(self):
        return self.data.author[0]

    def published(self):
        return self.data.pubdate

    def pdf(self):
        strs = ['/PUB_PDF','/EPRINT_PDF','/ADS_PDF']
        output = os.path.join(utils.pdf_read(),self.bibcode+'.pdf')
        # Does file allready exist?
        if os.path.exists(output):
            return output
        
        for i in strs:
            url = self._search_url+str(self.bibcode)+i
            f = self.download_file(url, output)
            # Did file download?
            if f is not None:
                return f

    def abstract(self):
        return self.data.abstract




class downloadArxiv(downloadGeneric):
    def __init__(self,id):
        self.id = id
        self.search_url = 'http://export.arxiv.org/api/query?search_query='+self.id
        self.get_data()

    def get_data(self):
        self.data = feedparser.parse(self.search_url)

    def title(self):
        return self.data['entries'][0]['title'].replace('\n','')

    def authors(self):
        return list([i['name'] for i in self.data['entries'][0]['authors']])

    def first_author(self):
        return self.data['entries'][0]['authors'][0]['name']

    def published(self):
        return self.data['entries'][0]['published']

    def pdf_url(self):
        for i in self.data['entries'][0]['links']:
            if 'title' in i:
                if i['title']=='pdf':
                    return i['href']

    def pdf(self):
        url = self.pdf_url()
        if url is None:
            raise ValueError("Bad URL")
        output = os.path.join(utils.pdf_read(),self.id+'.pdf')
        return self.download_file(url, output)

    def abstract(self):
        return self.data['entries'][0]['summary_detail']['value'].replace('\n','')


class Page(object):

    def make_header(self):
        header = Gtk.HBox()
        title_label = self.name()
        image = Gtk.Image()
        image.set_from_icon_name('window-close-symbolic', Gtk.IconSize.BUTTON)
        close_button = Gtk.Button()
        close_button.set_image(image)
        close_button.set_relief(Gtk.ReliefStyle.NONE)
        close_button.connect('clicked', self.on_tab_close)
        header.pack_start(title_label,
                          expand=True, fill=True, padding=0)
        header.pack_end(close_button,
                        expand=False, fill=False, padding=1)
        header.show_all()

        return header


    def on_tab_close(self, button):
        self.notebook.remove_page(self.page_num)
        self.page_num = -1


class searchPage(Page):
    def __init__(self, notebook, query):
        self._query = query

        self.page = None
        self.notebook = notebook
        self.page_num = -1    

    def add_page(self):
        pdfname = self.parse_query()
        self._page = pdfPage(self.notebook, pdfname)
        self._page.add_page()
        self.page = self._page.page
        return self.page

    def name(self):
        return Gtk.Label(label="search: " + str(self._query))

    def isnum(self,num):
        try:
            float(num)
            return True
        except ValueError:
            return False

    def parse_query(self):
        # What type of query is it?
        if any(i in self._query for i in ['http','www']):
            qtype = downloadADS(ident=self.process_url())
        elif any(i in self._query for i in ['arxiv','arixiv']) or (self.isnum(self._query) and '.' in self._query):
            qtype = downloadArxiv(self._query)
        elif len(self._query)==19 and self.isnum(self._query[0:4]):
            qtype = downloadADS(bibcode=self._query)
        else:
            raise NotImplementedError

        return qtype.pdf() 

    def process_url(self):
        res = {}

        if 'adsabs.harvard.edu' in self._query: # ADSABS
            q = self._query.split('/')
            if len(q[-1])==19:
                res['bibcode'] = q[-1]
            elif len(q[-2])==19:
                res['bibcode'] = q[-1]
            else:
                res['bibcode'] = None
        elif 'arxiv.org/' in self._query: #ARXIV
            res['arxiv'] = self._query.split('/')[-1]
        elif "iopscience.iop.org" in self._query: #ApJ, ApJS
            #http://iopscience.iop.org/article/10.3847/1538-4365/227/2/22/meta
            res['doi'] = self._query.partition('article/')[-1].replace('/meta','')
        elif 'academic.oup.com/mnras' in self._query: #MNRAS
            # https://academic.oup.com/mnras/article/433/2/1133/1747991
            # Fake some headers
            headers = {'user-agent': 'my-app/0.0.1'}
            r=requests.get(self._query,headers=headers)
            for i in r.text.split():
                if 'doi.org' in i and '>' in i:
                    break # Many matches but we want the line which has a href=url>
            res['doi'] = i.split('>')[1].split('<')[0].split('doi.org/')[1]
        elif 'aanda.org' in self._query: #A&A:
            #https://www.aanda.org/articles/aa/abs/2017/07/aa30698-17/aa30698-17.html
            #Resort to downloading webpage as the url is useless
            data = urllib.request.urlopen(self._query)
            html = data.read()
            ind = html.index(b'citation_bibcode')
            x = html[ind:ind+50].decode()
            #bibcodes are 19 characters, but the & in A&A gets converted to %26
            res['bibcode'] = str(x[27:27+21]).replace('%26','&')
        elif 'nature.com' in self._query: #nature
            #https://www.nature.com/articles/s41550-018-0442-z #plus junk after this
            if '?' in self._query:
                self._query = self._query[:self._query.index("?")]
            data = urllib.request.urlopen(self._query+'.ris')
            html = data.read().decode().split('\n')
            for i in html:
                if 'DO  -' in i:
                    doi = i.split()[-1]
                    res['doi'] = i.split()[-1]
                    break
        elif 'sciencemag.org' in self._query: #science
            #http://science.sciencemag.org/content/305/5690/1582
            data = urllib.request.urlopen(self._query)
            html = data.read()
            ind = html.index(b'citation_doi')
            doi = html[ind:ind+100].decode().split('/>')[0].split('=')[-1].strip().replace('"','')
            res['doi'] = doi
        elif 'PhysRevLett' in self._query: #Phys Review Letter
            #https://journals.aps.org/prl/abstract/10.1103/PhysRevLett.116.241103
            doi = '/'.join(self._query.split('/')[-2:])
            res['doi'] = doi
            
        return res


class pdfPage(Page):
    def __init__(self, notebook, filename, data=None):
        self._filename = filename
        self.filename = 'file://'+filename
        self.data = data
        self.doc = EvinceDocument.Document.factory_get_document(self.filename)

        self.page = None
        self.notebook = notebook
        self.page_num = -1


    def add_page(self):
        self.page = Gtk.HPaned()

        self.page.add1(self.show_info())
        self.page.add2(self.show_pdf())

        return self.page

    def show_pdf(self):
       scroll = Gtk.ScrolledWindow()
       view = EvinceView.View()
       model = EvinceView.DocumentModel()
       model.set_document(self.doc)
       view.set_model(model)
       scroll.add(view)
       return scroll  

    def show_info(self):    
        info = Gtk.Grid()

        info.set_column_homogeneous(True)
        info.set_orientation(Gtk.Orientation.VERTICAL)

        #TODO: Extend this with actual data
        info.add(Gtk.Label(label='Title'))
        info.add(Gtk.Label(label='Authors'))
        info.add(Gtk.Label(label='Journal'))
        info.add(Gtk.Label(label='Date Published'))
        info.add(Gtk.Label(label='Date Added'))
        info.add(Gtk.Label(label='Arixv ID'))
        info.add(Gtk.Label(label='Bibcode'))

        info.add(Gtk.Label(label='Abstract'))

        info.add(Gtk.Label(label='References'))
        info.add(Gtk.Label(label='Citations'))
        info.add(Gtk.Label(label='Images'))
        info.add(Gtk.Label(label='Bibtex'))

        return info 

    def name(self):
        return Gtk.Label(label=os.path.basename(self.filename))

    def arixv_num(self):
        page = self.doc.get_page(0)
        text = self.doc.get_text(page)

        for i in text.split('\n'):
            if 'arXiv:' in i :
                self.arixv = i.split()[0][len('arXiv:'):]

        return None

    def get_details(self):
        if self.arixv is None:
            self.arixv_num()

        


class OptionsMenu(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="Options")

        grid = Gtk.Grid()
        self.add(grid)

        self.ads_entry = Gtk.Entry()
        self.ads_entry.set_width_chars(50)
        self.ads_entry.set_text(utils.ads_read())

        self.orcid_entry = Gtk.Entry()
        self.orcid_entry.set_text(utils.orcid_read())
        self.orcid_entry.set_width_chars(50)

        label = "Choose Folder"
        if utils.pdf_read() is not None:
            label = utils.pdf_read()

        self.folder_entry = Gtk.Button(label=label)
        self.folder_entry.connect("clicked", self.on_file_clicked)



        ads_label = Gtk.Label(label='ADSABS ID')
        orcid_label = Gtk.Label(label='ORCID ID')
        file_label = Gtk.Label(label='Save folder')

        save_button_ads = Gtk.Button(label="Save")
        save_button_ads.connect("clicked", self.save_ads)

        save_button_orcid = Gtk.Button(label="Save")
        save_button_orcid.connect("clicked", self.save_orcid)

        grid.add(ads_label)
        grid.attach_next_to(self.ads_entry,ads_label,
                            Gtk.PositionType.RIGHT,1,1)
        grid.attach_next_to(save_button_ads,self.ads_entry,
                            Gtk.PositionType.RIGHT,1,1)        

        grid.attach_next_to(orcid_label,ads_label,
                            Gtk.PositionType.BOTTOM,1,1)
        grid.attach_next_to(self.orcid_entry,orcid_label,
                            Gtk.PositionType.RIGHT,1,1)
        grid.attach_next_to(save_button_orcid,self.orcid_entry,
                            Gtk.PositionType.RIGHT,1,1)  

        grid.attach_next_to(file_label,orcid_label,
                            Gtk.PositionType.BOTTOM,1,1)
        grid.attach_next_to(self.folder_entry,file_label,
                            Gtk.PositionType.RIGHT,1,1)        

    def save_ads(self, button):
        value = self.ads_entry.get_text()
        utils.ads_save(value)

    def save_orcid(self, button):
        value = self.orcid_entry.get_text()
        utils.orcid_save(value)    



    def on_file_clicked(self, widget):
        dialog = Gtk.FileChooserDialog(
            title="Please choose a folder", parent=self, action=Gtk.FileChooserAction.SELECT_FOLDER
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL,
            Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN,
            Gtk.ResponseType.OK,
        )

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            f = dialog.get_filename()
            widget.set_label(f)
            utils.pdf_save(f)
            
        dialog.destroy()

def main():
    win = MyWindow()
    win.connect("destroy", Gtk.main_quit)
    win.set_hide_titlebar_when_maximized(False)
    win.maximize()
    win.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
