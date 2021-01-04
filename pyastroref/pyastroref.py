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
from . import database

import gi
gi.require_version("Gtk", "3.0")
gi.require_version('EvinceDocument', '3.0')
gi.require_version('EvinceView', '3.0')
from gi.repository import GLib, Gtk, GObject, Gio, GdkPixbuf
from gi.repository import EvinceDocument
from gi.repository import EvinceView


EvinceDocument.init()

_pages = {}
_settings = {}

_THREADS_ON=True

class MainWindow(Gtk.Window):
    def __init__(self):
        self._init = False
        self.settings = {}
        self.pages = {}

        Gtk.Window.__init__(self, title="pyAstroRef")

        self.setup_headerbar()
        self.setup_search_bar()
        self.setup_search_loc()

        self.setup_notebook()
        self.setup_grid()       

        # Make empty databse if not allready existing
        self.db = database.database()

        self.make_main_page()

        self.warn_ads_not_set()
        self._init = True


    def on_click_load_options(self, button):
        win = OptionsMenu()
        win.show_all()

    def on_click_search(self, button):
        query = self.search.get_text()

        if len(query) == 0:
            return

        Search(self.notebook, query)

    def make_main_page(self):
        self.main_page = mainPage(self.notebook, data = self.db.get_all())
        self.notebook.prepend_page(self.main_page.page(), Gtk.Label(label='Home'))
        self.notebook.set_tab_reorderable(self.main_page.page(), False)
        self.notebook.connect('page-reordered', self.on_reorder)


    def setup_search_bar(self):
        self.search = Gtk.SearchEntry()
        self.search.set_width_chars(100)
        self.search.connect("activate",self.on_click_search)

        self.search.set_can_default(True)
        self.set_default(self.search)
        self.search.set_hexpand(True)

    def setup_search_loc(self):
        search_locs = ['Local','ADSABS','Arxiv']

        self.search_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)


        combo = Gtk.ComboBoxText()
        combo.set_entry_text_column(0)
        combo.connect('changed', self.on_search_loc_change)
        for i in search_locs:
            combo.append_text(i)
        
        combo.set_active(0)
        self.search_box.pack_start(combo, False, False, True)

    def setup_bibtex_import(self):
        self.button_bibtex = Gtk.Button()
        self.button_bibtex.connect("clicked", self.on_click_load_options)
        image = Gtk.Image()
        image.set_from_icon_name('list-add', Gtk.IconSize.BUTTON)
        self.button_bibtex.set_image(image)



    def on_search_loc_change(self, combo):
       _settings['search_source'] = combo.get_active_text()


    def setup_headerbar(self):
        self.options_menu()
        self.rssfeeds()
        self.setup_bibtex_import()

        hb = Gtk.HeaderBar()
        hb.set_show_close_button(True)
        hb.props.title = "pyAstroRef"
        self.set_titlebar(hb)

        hb.pack_start(self.button_opt)
        hb.pack_start(self.button_rss)
        hb.pack_start(self.button_bibtex)


    def rssfeeds(self):
        self.button_rss = Gtk.Button()

        icon_filename = os.path.join(os.path.dirname(__file__),"../","icons","Generic_Feed-icon.svg")
        self.button_rss.connect("clicked", self.on_click_load_rssfeeds)

        size = Gtk.IconSize.lookup(Gtk.IconSize.BUTTON)
        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_size(icon_filename,size.width,size.height)

        image = Gtk.Image()
        image.set_from_pixbuf(pixbuf)
        self.button_rss.set_image(image)


    def on_click_load_rssfeeds(self, button):
        win = OptionsMenu()
        win.show_all()


    def options_menu(self):
        self.button_opt = Gtk.Button()
        self.button_opt.connect("clicked", self.on_click_load_options)
        image = Gtk.Image()
        image.set_from_icon_name('open-menu-symbolic', Gtk.IconSize.BUTTON)
        self.button_opt.set_image(image)

    def setup_notebook(self):
        self.notebook = Gtk.Notebook()
        self.notebook.set_hexpand(True)
        self.notebook.set_vexpand(True)
        self.notebook.set_tab_pos(Gtk.PositionType.LEFT)

        self.notebook.connect('switch-page', self.refresh_notebook)

        
    def setup_grid(self):
        self.grid = Gtk.Grid()
        self.grid.set_orientation(Gtk.Orientation.VERTICAL)

        self.add(self.grid)

        self.grid.add(self.search)

        self.grid.attach_next_to(self.search_box,self.search,
                                Gtk.PositionType.LEFT,1,1)

        self.grid.attach_next_to(self.notebook,self.search_box,
                             Gtk.PositionType.BOTTOM,2,1) 
        #self.grid.add(self.notebook)



    def warn_ads_not_set(self):

        t = utils.ads_read()
        if t is None or len(t)==0:
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

    def refresh_notebook(self, notebook, page, page_num):
        if page_num == 0 and self._init:
            self.main_page.refresh(self.db.get_all())


    def on_reorder(self, notebook, child, number):
        if number == 0:
            notebook.reorder_child(self.main_page.page(), 0)


class Search(object):
    def __init__(self, notebook, query):
        self.query = query
        self.notebook = notebook

        self.new_pdf_page(query)

    def new_pdf_page(self, query):
        def search():
            GLib.idle_add(self.new_page,searchPage,query)

        if _THREADS_ON:
            thread = threading.Thread(target=search)
            thread.daemon = True
            thread.start()
        else:
            search()

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



class downloadADS(object):
    _fields = ['bibcode','title','author','year','abstract','year',
                        'pubdate','bibstem','alternate_bibcode']
    _search_url = 'https://ui.adsabs.harvard.edu/link_gateway/'

    def __init__(self,bibcode=None,ident=None):
        ads.config.token = utils.ads_read()
        
        self.bibcode = bibcode
        self.ident = ident

        if self.bibcode is not None:
            self.get_data()
        if self.ident is not None:
            self.get_bibcode()

        self.add_to_db()
    
    def get_data(self):
        self.data = list(ads.SearchQuery(bibcode=self.bibcode,
                    fl=self._fields,rows=1))[0]

    def get_bibcode(self):
        if 'bibcode' in self.ident:
            self.bibcode = self.ident['bibcode']
            self.get_data()
            return

        if 'doi' in self.ident:
            self.data = list(ads.SearchQuery(doi=self.ident['doi'],fl=self._fields,rows=1))[0]
        elif 'arxiv' in self.ident:
            self.data = list(ads.SearchQuery(q=self.ident['arxiv'],fl=self._fields,rows=1))[0]
        else:
            raise ValueError("Didnt match ident, got",self.ident)

        self.bibcode = self.data.bibcode

    @property
    def title(self):
        return self.data.title[0]

    @property
    def authors(self):
        return  '; '.join(self.data.author)

    @property
    def first_author(self):
        return self.data.author[0]

    @property
    def pubdate(self):
        return self.data.pubdate

    @property
    def journal(self):
        return self.data.bibstem[0]

    @property
    def filename(self):
        return self.bibcode+'.pdf'

    @property
    def year(self):
        return self.data.year

    def pdf(self):
        strs = ['/PUB_PDF','/EPRINT_PDF','/ADS_PDF']
        output = os.path.join(utils.pdf_read(),self.bibcode+'.pdf')
        # Does file allready exist?
        if os.path.exists(output):
            return output
        
        for i in strs:
            url = self._search_url+str(self.bibcode)+i
            f = utils.download_file(url, output)
            # Did file download?
            if f is not None:
                return f

    @property
    def abstract(self):
        return self.data.abstract

    def name(self):
        return str(self.first_author())+' '+ str(self.year())


    def add_to_db(self):
        db = database.database()
        fields = db.fields()
        data = {}
        for i in fields:
            try:
                data[i] = str(getattr(self, i))
            except AttributeError:
                data[i] = ''
        db.add(data)



class downloadArxiv(object):
    def __init__(self,id):
        self.id = id
        self.search_url = 'http://export.arxiv.org/api/query?search_query='+self.id
        self.get_data()

    def get_data(self):
        self.data = feedparser.parse(self.search_url)

    @property
    def title(self):
        return self.data['entries'][0]['title'].replace('\n','')

    @property
    def authors(self):
        return '; '.join([i['name'] for i in self.data['entries'][0]['authors']])

    @property
    def first_author(self):
        return self.data['entries'][0]['authors'][0]['name']

    @property
    def pubdate(self):
        return self.data['entries'][0]['published']

    @property
    def journal(self):
        return 'Arxiv'

    @property
    def year(self):
        return self.pubdate()[0:4]

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
        return utils.download_file(url, output)

    @property
    def abstract(self):
        return self.data['entries'][0]['summary_detail']['value'].replace('\n','')

    def name(self):
        return str(self.first_author())+' '+ str(self.published())


    def add_to_db(self):
        db = database.database()
        fields = db.fields()
        data = {}
        for i in fields:
            try:
                data[i] = str(getattr(self, i))
            except AttributeError:
                data[i] = ''
        db.add(data)


class Page(object):

    def make_header(self):
        header = Gtk.HBox()
        title_label =  Gtk.Label(label=self.name())
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
        self._query = query.strip()

        self.page = None
        self.notebook = notebook
        self.page_num = -1    

    def add_page(self):
        pdfname = self.parse_query()
        self._page = pdfPage(self.notebook, pdfname)
        self._page.add_page()
        self.page = self._page.page
        self.name = self._page.name
        return self.page

    def isnum(self,num):
        try:
            float(num)
            return True
        except ValueError:
            return False

    def parse_query(self):
        # What type of query is it?
        if any(i in self._query for i in ['https://','http://','www.']):
            qtype = downloadADS(ident=utils.process_url(self._query))
        elif (
                any(i in self._query for i in ['arxiv','arixiv']) or 
                (self.isnum(self._query) and '.' in self._query) or
                _settings['search_source']=='Arxiv'
            ):
            qtype = downloadArxiv(self._query)
        elif (
                len(self._query)==19 and self.isnum(self._query[0:4]) or 
                _settings['search_source']=='ADSABS'
            ): #Bibcode
            qtype = downloadADS(bibcode=self._query)
        else:
            raise NotImplementedError

        # Add to database
        qtype.add_to_db()

        return qtype.pdf()


class pdfPage(Page):
    def __init__(self, notebook, filename, data=None):
        self.data = data

        self.doc = None

        self._filename = filename

        if self._filename is not None:
            self.filename = 'file://'+filename
            self.doc = EvinceDocument.Document.factory_get_document(self.filename)

        self.notebook = notebook
        self.page_num = -1

    def add_page(self):
        self.page = Gtk.HPaned()

        self.page.add1(self.show_info())
        self.page.add2(self.show_pdf())

        return self.page

    def show_pdf(self):

        if self.doc is None:
            scroll = Gtk.HBox()
            label = Gtk.Label(label="Can not show file")
            scroll.pack_start(label, True, True, 0)
        else:
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
        if self.doc is None:
            return "Bad file"
        else:
            return os.path.basename(self.filename)



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

class mainPage(object):
    def __init__(self, notebook, data):
        # Setting up the self.grid in which the elements are to be positionned
        self.grid = Gtk.Grid()
        self.grid.set_column_homogeneous(True)
        self.grid.set_row_homogeneous(True)
        self.data = data

        self.notebook = notebook
        self.results = displayResults(self.notebook, self.data)
        self.grid.attach(self.results.page(), 0, 0, 8, 10)
        self.grid.show_all()

    def refresh(self, data):
        self.data = data
        self.results.refresh(self.data)
        self.grid.show_all()

    def page(self):
        return self.grid


class displayResults(object):
    cols = ["Title", "First Author", "Year", "Authors", "Journal", "PDF", "Bibtex"]

    def __init__(self, notebook, data=None):
        self.notebook = notebook

        self.data = data
        self.liststore = Gtk.ListStore(*[str]*len(self.cols))
        self.make_liststore()
        self.make_treeview()


    def make_liststore(self):
        # Creating the ListStore model
        for paper in self.data:

            pdficon = 'go-down'
            if os.path.exists(os.path.join(utils.pdf_read(),paper['filename'])):
                pdficon = 'x-office-document'


            authors = paper['authors'].split(';')[1:]
            if len(authors) > 5:
                authors = authors[0:5]
                authors.append('et al')
            authors = '; '.join([i.strip() for i in authors])

            self.liststore.append([
                paper['title'],
                paper['first_author'],
                paper['year'],
                authors,
                paper['journal'],
                pdficon,
                'edit-copy'
            ])

    def make_treeview(self):
        # creating the treeview and adding the columns
        self.treeviewsorted = Gtk.TreeModelSort(self.liststore)
        self.treeview = Gtk.TreeView.new_with_model(self.treeviewsorted)
        for i, column_title in enumerate(self.cols):
            if column_title == 'PDF' or column_title == 'Bibtex':
                renderer = Gtk.CellRendererPixbuf()
                column = Gtk.TreeViewColumn(column_title, renderer, icon_name=i)
                column.set_expand(False)
            else:
                renderer = Gtk.CellRendererText()
                renderer.props.wrap_width = 100
                renderer.props.wrap_mode = Gtk.WrapMode.WORD
                column = Gtk.TreeViewColumn(column_title, renderer, text=i)
                column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
                column.set_resizable(True)
                column.set_sort_column_id(i)
                if column_title == 'Title':
                    column.set_expand(True)

            self.treeview.append_column(column)

        # setting up the layout, putting the treeview in a scrollwindow
        self.scrollable_treelist = Gtk.ScrolledWindow()
        self.scrollable_treelist.set_vexpand(True)
        self.scrollable_treelist.set_hexpand(True)

        self.scrollable_treelist.add(self.treeview)
        self.treeview.connect('row-activated' , self.button_press_event)

    def button_press_event(self, treeview, path, view_column):
        cp = self.treeviewsorted.convert_path_to_child_path(path)
        row = cp.get_indices()[0]
        Search(self.notebook, self.data[row]['bibcode'])

    def refresh(self, data):
        self.data = data
        self.liststore.clear()
        self.make_liststore()

    def page(self):
        return self.scrollable_treelist


def main():
    win = MainWindow()
    win.connect("destroy", Gtk.main_quit)
    win.set_hide_titlebar_when_maximized(False)
    win.maximize()
    win.show_all()
    Gtk.main()


if __name__ == "__main__":
    main()
