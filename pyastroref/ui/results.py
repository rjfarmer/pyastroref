# SPDX-License-Identifier: GPL-2.0-or-later

import os
import sys
import threading
import vcr
import hashlib
import datetime
from pathlib import Path
import pickle

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk, GObject, Gdk

from . import utils, libraries, pdf

import pyastroapi

_fields = "abstract,author,bibcode,pubdate,title,pub,year,citation_count,reference,orcid_user,bibstem"

class ResultsPage(Gtk.VBox):
    def __init__(self, notebook, name):
        Gtk.VBox.__init__(self)
        self.notebook = notebook
        self.name = name

        self.journal = pyastroapi.journal()

        self.set_vexpand(True)
        self.set_hexpand(True)

        self.header = ResultsHeader(self)
        
        self.setup_scroll()
        self.setup_notebook()

        self.list = ResultsList()
        self.scroll.add(self.list)

        self.show_all()

    def setup_scroll(self):
        self.scroll = Gtk.ScrolledWindow()
        self.add(self.scroll)

    def setup_notebook(self):
        self.notebook.append_page(self, self.header)
        self.notebook.set_tab_reorderable(self, True)
        self.notebook.show_all()

    def download(self):
        def threader():
            self.data()
            self.list.align_my_header()
            self.header.spin_off()

        #thread = threading.Thread(target=threader)
        #thread.daemon = True
        threader()

    def add_paper(self, paper):
        self.list.add(ResultsRow(paper, self.notebook))

    def cache_file(self, time):
        file = Path(os.path.join(utils.settings.cache,self.hash()))

        if os.path.exists(file):
            yesterday = datetime.date.today() - datetime.timedelta(days=time)
            last_modified = datetime.date.fromtimestamp(file.stat().st_mtime)
            if last_modified < yesterday:
                os.remove(file)
        return file

    def data(self):
        if os.path.exists(self.cache_filename):
            print("Local")
            self.data_local()
        else:
            print("Remote")
            self.data_remote()

    def data_remote(self):
        iter = self.get_iter()

        if iter is None:
            return

        for paper in iter:
            art = pyastroapi.article(data=paper)
            self.journal.add_articles([art])
            self.add_paper(art)

        with open(self.cache_filename,'wb') as f:
            pickle.dump(self.journal,f)


    def data_local(self):
        with open(self.cache_filename,'rb') as f:
            self.journal = pickle.load(f)

        if len(self.journal) == 0:
            self.data_remote()
        else:
            for paper in self.journal.values():
                self.add_paper(paper)


class ResultsSearch(ResultsPage):
    def __init__(self, query, notebook, name = None):
        self.query = query
        if name is None:
            name  = self.query

        super().__init__(notebook, name)

        self.cache_time = 1 #days
        self.cache_filename = self.cache_file(time=self.cache_time)
        self.download()

    def get_iter(self):
        return pyastroapi.search(self.query,fields=_fields,limit=-1,dbg=True)

    def hash(self):
        var = self.query + _fields
        return hashlib.md5(var.encode('utf-8')).hexdigest()


class ResultsOrcid(ResultsPage):
    def __init__(self, query, notebook, name = None):
        self.query = query
        if name is None:
            name  = self.query

        super().__init__(notebook, name)

        self.cache_time = 1 #days
        self.cache_filename = self.cache_file(time=self.cache_time)
        self.download()

    def get_iter(self):
        return pyastroapi.orcid(self.query,fields=_fields,limit=-1,dbg=True)

    def hash(self):
        var = self.query + _fields
        return hashlib.md5(var.encode('utf-8')).hexdigest()


class ResultsArxiv(ResultsPage):
    def __init__(self, notebook):

        self.name = 'Arxiv'
        super().__init__(notebook, self.name)

        self.cache_time = 1 #days
        self.cache_filename = self.cache_file(time=self.cache_time)
        self.download()

    def get_iter(self):
        return pyastroapi.astro_ph(fields=_fields,limit=-1,dbg=True)

    def hash(self):
        var = 'arxiv'+ str(datetime.datetime.today()) + _fields
        return hashlib.md5(var.encode('utf-8')).hexdigest()


class ResultsCites(ResultsPage):
    def __init__(self, paper, notebook, name = None):
        self.paper = paper
        if name is None:
            name  = f"Cites: {self.paper.name}"

        super().__init__(notebook, name)

        self.cache_time = 1 #days
        self.cache_filename = self.cache_file(time=self.cache_time)
        self.download()

    def get_iter(self):
        return pyastroapi.citations(self.paper.bibcode,fields=_fields)

    def hash(self):
        var = 'cites ' + self.paper.bibcode + _fields
        return hashlib.md5(var.encode('utf-8')).hexdigest()

class ResultsRefs(ResultsPage):
    def __init__(self, paper, notebook, name = None):
        self.paper = paper
        if name is None:
            name  = f"Refs: {self.paper.name}"

        super().__init__(notebook, name)

        self.cache_time = 14 #days
        self.cache_filename = self.cache_file(time=self.cache_time)
        self.download()

    def get_iter(self):
        return pyastroapi.references(self.paper.bibcode,fields=_fields)

    def hash(self):
        var = 'refs' + self.paper.bibcode + _fields
        return hashlib.md5(var.encode('utf-8')).hexdigest()


class ResultsLibrary(ResultsPage):
    def __init__(self, library, notebook, name = None):
        self.lib = library

        if name is None:
            name  = self.lib

        super().__init__(notebook, name)
        self.cache_time = 0.1 #days
        self.cache_filename = self.cache_file(time=self.cache_time)
        self.download()

    def get_iter(self):
        x = libraries.get(self.lib)

        if x is not None:
            return x.values

    def hash(self):
        var = 'library ' + self.lib + _fields
        return hashlib.md5(var.encode('utf-8')).hexdigest()


class ResultsHeader(Gtk.EventBox):
    def __init__(self, page):
        Gtk.EventBox.__init__(self)
        self.page = page
        self.notebook = page.notebook
        self.name = page.name

        self.spinner = Gtk.Spinner()
        self.header = Gtk.HBox()
        self.popover = Gtk.Popover()
        self.title_label = Gtk.Label(label=self.name)

        self.setup_close_button()

        # Header box
        self.spin_on()
        self.header.pack_start(self.title_label,
                          expand=True, fill=True, padding=0)
        self.header.pack_end(self.spinner,
                        expand=False, fill=False, padding=0)
        self.add(self.header)

        #self.setup_buttons()

        self.header.show_all()
        self.show_all()

    def setup_close_button(self):
        self.close_button = Gtk.Button()
        image = Gtk.Image()
        image.set_from_icon_name('window-close', Gtk.IconSize.MENU)
        self.close_button.set_image(image)
        self.close_button.set_relief(Gtk.ReliefStyle.NONE)
        self.close_button.connect('clicked', self.on_tab_close)

    def on_tab_close(self, button):
        self.notebook.remove_page(self.notebook.page_num(self.page))

    def spin_on(self):
        GLib.idle_add(self.spinner.start)

    def spin_off(self):
        def f():
            self.spinner.stop()
            self.header.remove(self.spinner)
            self.header.pack_end(self.close_button,
                            expand=False, fill=False, padding=0)
            self.header.show_all()
        GLib.idle_add(f)


    # def button_press(self, widget, event):
    #     if event.button == Gdk.BUTTON_PRIMARY:
    #         self.notebook.set_current_page(self.notebook.page_num(self.page))
    #         return True
    #     elif event.button == Gdk.BUTTON_SECONDARY:
    #         #make widget popup
    #         self.popover.popup()
    #         return True
    #     return False


class ResultsList(Gtk.ListBox):
    def __init__(self):
        Gtk.ListBox.__init__(self)
        self.set_selection_mode(Gtk.SelectionMode.NONE)
        self.header = Gtk.HBox()
        self.show_all()

    def align_my_header(self,*args):
        def set_header_func(self, row, before ,*args):
            print(args)
            row = self.get_row_at_index(0)
            if row is None:
                return

            self.header = Gtk.HBox()
            labels = ["Title", "First author", "Authors", "Journal",
                    "Year", "Refs", "Cites","Bibtex","PDF" ]
            
            for l,pack in zip(labels,row.get_packing()):
                label = Gtk.Label(l)
                self.header.pack_start(label,pack.expand,pack.fill,pack.padding)

            row.connect('realize', row.set_header_size, self.header)

            self.header.show_all()

        self.set_header_func = set_header_func

class ResultsRow(Gtk.ListBoxRow):
    def __init__(self,paper, notebook):
        Gtk.ListBoxRow.__init__(self)
        
        self.box = Gtk.HBox()
        self.notebook = notebook
        self.paper = paper
        self.filename = None
        self.add(self.box)

        self.setup_title()
        self.setup_first_author()
        self.setup_authors()
        self.setup_journal()
        self.setup_cites()
        self.setup_refs()
        self.setup_year()
        self.setup_bibtex()
        self.setup_pdf()

        self.box.pack_start(self.title, True, True, 10)
        self.box.pack_start(self.first_author, False, False, 10)
        self.box.pack_start(self.authors, False, False, 10)
        self.box.pack_start(self.journal, False, True, 10)
        self.box.pack_start(self.year, False, True, 10)
        self.box.pack_start(self.refs, False, True, 10)
        self.box.pack_start(self.cites, False, True, 10)
        self.box.pack_start(self.bibtex, False, True, 10)
        self.box.pack_start(self.pdf, False, True, 10)

        self.box.show_all()
        self.show_all()

    def get_width(self):
        width = []
        for child in self.box.get_children():
            width.append(child.get_allocated_width())
        return width

    def get_packing(self):
        packing = []
        for child in self.box.get_children():
            packing.append(self.box.query_child_packing(child))
        return packing

    def set_header_size(self, row, header):
        if self.get_index() != 0:
            return

        width = self.get_width()
        for child,w in zip(header.get_children(),width):
            print(child,w)
            child.set_size_request(w,-1)

        self.set_header(header)
        header.show_all()
        self.show_all()

    def setup_title(self):
        self.title = Gtk.Label(self.paper.title.strip())
        self.title.set_justify(Gtk.Justification.LEFT)
        self.title.set_xalign(0)
        self.title.set_hexpand(False)
        self.title.set_selectable(True)
        self.title.set_line_wrap(True)

    def setup_first_author(self):
        self.first_author = self.setup_author(self.paper.first_author,0)

    def setup_author(self,name,index):
        author = Gtk.Label()
        author.set_markup(f"<a href='{index}'>{name}</a>")
        author.connect("activate-link", self.author_on_link_clicked)
        return author

    def setup_year(self):
        self.year = Gtk.Label(self.paper.year)

    def setup_bibtex(self):
        self.bibtex = Gtk.Button()
        image = Gtk.Image()
        if os.path.exists(os.path.join(utils.settings.bibtex_cache,self.paper.bibcode)):
            image.set_from_icon_name('x-office-document', Gtk.IconSize.MENU)
        else:
            image.set_from_icon_name('go-down', Gtk.IconSize.MENU)
        self.bibtex.set_image(image)
        self.bibtex.set_relief(Gtk.ReliefStyle.NONE)

    def setup_pdf(self):
        self.pdf = Gtk.Button()
        image = Gtk.Image()

        try:
            self.filename = os.path.join(utils.settings.pdffolder,self.paper.pdf.filename())
        except ValueError:
            self.filename = None # No pdf available

        if self.filename is None:
            image.set_from_icon_name('window-close', Gtk.IconSize.MENU)
        elif os.path.exists(self.filename):
            image.set_from_icon_name('x-office-document', Gtk.IconSize.MENU)
        else:
            image.set_from_icon_name('go-down', Gtk.IconSize.MENU)
        self.pdf.set_image(image)
        self.pdf.set_relief(Gtk.ReliefStyle.NONE)


    def author_on_link_clicked(self, label, uri):
        try:
            orcid = self.paper.orcid_user[int(uri)] 
        except KeyError:
            orcid = '-'
        if orcid is not '-':
            print(f'orcid:"{orcid}"')
            ResultsSearch(f'orcid:"{orcid}"', self.notebook, name = label.get_text())
        else:
            print(f'author:"{label.get_text()}"')
            ResultsSearch(f'author:"{label.get_text()}"', self.notebook, name =label.get_text() )
        return True

    def setup_journal(self):
        self.journal = Gtk.Label()
        pub = GLib.markup_escape_text(self.paper.bibstem[0])
        self.journal.set_markup(f"<a href='publisher'>{pub}</a>")
        self.journal.set_line_wrap(True)
        self.journal.set_max_width_chars(26)

    def setup_cites(self):
        self.cites = Gtk.Label()
        count = self.paper.citation_count
        if count:
            self.cites.set_markup(f"<a href='citations'>{count}</a>")
            self.cites.connect("activate-link", self.cites_on_link_clicked)
        else:
            self.cites.set_text('0')
        

    def setup_refs(self):
        self.refs = Gtk.Label()
        count = self.paper.reference_count()
        if count:
            self.refs.set_markup(f"<a href='references'>{count}</a>")
            self.refs.connect("activate-link", self.refs_on_link_clicked)
        else:
            self.refs.set_text('0')

    def setup_authors(self):
        num = 4
        self.authors = Gtk.VBox()
        authors = self.paper.authors

        if len(authors) <= num+1:
            for index,author in enumerate(authors[1:num+1]):
                self.authors.pack_start(self.setup_author(author, index),False,False,0)
        else:
            for index,author in enumerate(authors[1:num+1]):
                self.authors.pack_start(self.setup_author(author, index),False,False,0)
            
            self.popover = Gtk.Popover()

            scroll = Gtk.ScrolledWindow()
            scroll.set_policy(Gtk.PolicyType.NEVER,Gtk.PolicyType.ALWAYS)
            scroll.set_vexpand(True)
            scroll.set_hexpand(True)
            scroll.set_min_content_height(50)

            vbox = Gtk.VBox()

            for index,author in enumerate(authors[num+1:]):
                vbox.pack_start(self.setup_author(author, num+index),True,True,5)
            
            scroll.add(vbox)
            vbox.show_all()
            scroll.show_all()
            self.popover.add(scroll)
            self.popover.set_position(Gtk.PositionType.BOTTOM)

            etal = Gtk.MenuButton(label="et al.", popover=self.popover)
            etal.set_relief(Gtk.ReliefStyle.NONE)

            self.authors.pack_start(etal,False,False,0)


        self.authors.show_all()

    def refs_on_link_clicked(self, label, uri):
        print(f'references:({self.paper.bibcode})')
        ResultsRefs(self.paper, self.notebook)
        return True

    def cites_on_link_clicked(self, label, uri):
        print(f'citations:({self.paper.bibcode})')
        ResultsCites(self.paper, self.notebook)
        return True


# class JournalPage(Gtk.VBox):
#     def __init__(self, target, notebook, name):
#         Gtk.VBox.__init__(self)
#         self.has_search_open=False

#         self.target = target
#         self.notebook = notebook
#         self.scroll = Gtk.ScrolledWindow()

#         self.store = JournalStore(name)
#         self.store_view = JournalView(self.notebook, self.store)
#         self.header = JournalMenu(self.notebook, self, name)
#         self.setup_sb()

#         self.pack_start(self.sb,False,False,0)

#         self.add(self.scroll)

#         self.astroref_name = name
#         self.set_vexpand(True)
#         self.set_hexpand(True)
#         self.scroll.add(self.store_view.treeview)

#         self.notebook.append_page(self, self.header)
#         self.notebook.set_tab_reorderable(self, True)
#         self.notebook.show_all()

#         self.header.spin_on()
#         self.download()

#         self.show_all() 
#         self.scroll.show_all()
#         self.notebook.show_all()
#         self.header.show_all()

#     def download(self):
#         def threader():
#             self.store.make(self.target, self.update_data)
#             self.header.spin_off()


#         thread = threading.Thread(target=threader)
#         thread.daemon = True
#         GLib.idle_add(thread.start)

#     def setup_sb(self):
#         self.sb = Gtk.SearchEntry() 
#         self.sb.connect("changed", self.store.refresh_results)
#         self.sb.grab_focus_without_selecting()

#     def update_data(self, paper):
#         self.header.set_data(paper)
#         self.store_view.set_data(paper) 


# class JournalMenu(Gtk.EventBox):
#     def __init__(self, notebook, page, name):
#         Gtk.EventBox.__init__(self)

#         self.notebook = notebook
#         self.page = page
#         self.name = name

#         self.journal = pyastroapi.articles.journal()

#         self.spinner = Gtk.Spinner()
#         self.header = Gtk.HBox()
#         self.popover = Gtk.Popover()
#         self.title_label = Gtk.Label(label=self.name)

#         self.setup_close_button()

#         self.spin_on()
#         self.header.pack_start(self.title_label,
#                           expand=True, fill=True, padding=0)
#         self.header.pack_end(self.spinner,
#                         expand=False, fill=False, padding=0)

#         self.setup_buttons()

#         self.header.show_all()
#         self.show_all()


#     def set_data(self,paper):
#         self.journal.add_articles([paper])

#     def setup_close_button(self):
#         self.close_button = Gtk.Button()
#         image = Gtk.Image()
#         image.set_from_icon_name('window-close', Gtk.IconSize.MENU)
#         self.close_button.set_image(image)
#         self.close_button.set_relief(Gtk.ReliefStyle.NONE)
#         self.close_button.connect('clicked', self.on_tab_close)

#     def setup_buttons(self):
#         self.button = {}

#         self.vbox = Gtk.VBox(orientation=Gtk.Orientation.VERTICAL)

#         buttons = ['copy_bibtex','add_lib','save_search','close']
#         labels = ["Copy BibTex","Add all to library","Save search","Close"]
#         seps = [True, False, True, False, False]
#         actions = [self.bp_bib,self.bp_add_lib,self.bp_save_search,self.bp_close]

#         for button, label, action,sep in zip(buttons, labels, actions, seps):
#             self.button[button] = Gtk.Button.new_with_label(label)
#             self.vbox.pack_start(self.button[button], False, True, 0)
#             self.button[button].connect('button-press-event', action)
#             if sep:
#                 self.vbox.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, True, 10)

#         self.vbox.show_all()

#         self.popover.add(self.vbox)
#         self.popover.set_position(Gtk.PositionType.BOTTOM)
        
#         self.popover.set_relative_to(self.header)

#         self.add(self.header)

#         self.connect("button-press-event", self.button_press)


#     def on_tab_close(self, button):
#         self.notebook.remove_page(self.notebook.page_num(self.page))

#     def button_press(self, widget, event):
#         if event.button == Gdk.BUTTON_PRIMARY:
#             self.notebook.set_current_page(self.notebook.page_num(self.page))
#             return True
#         elif event.button == Gdk.BUTTON_SECONDARY:
#             #make widget popup
#             self.popover.popup()
#             return True
#         return False

#     def spin_on(self):
#         self.spinner.start()

#     def spin_off(self):
#         self.spinner.stop()
#         self.header.remove(self.spinner)
#         self.header.pack_end(self.close_button,
#                         expand=False, fill=False, padding=0)
#         self.header.show_all()


#     def bp_bib(self, widget, event):
#         if len(self.journal):
#             utils.clipboard(self.data.bibtex())
#             utils.show_status("Bibtex downloaded")
#         return True

#     def bp_add_lib(self, widget, event):
#         if len(self.journal):
#             libraries.Add2Lib(self.data.bibcodes())
#         return True

#     def bp_close(self, widget, event):
#         self.on_tab_close(widget)

#     def bp_save_search(self, widget, event):
#         saved_search.AddSavedSearch(self.page.astroref_name)

# _cols = ["Title", "First Author", "Year", "Authors", "Journal","References", "Citations", 
#         "PDF", "Bibtex","bibcode"]

# class JournalStore(Gtk.ListStore):
#     def __init__(self, name):
#         Gtk.ListStore.__init__(self, *[str]*len(_cols))
#         self.journal = pyastroapi.articles.journal()
#         self.name = name
#         self.clear()

#     def make(self, target, callback):
#         hash = hashlib.sha256()
#         hash.update(self.name.encode())
#         #with vcr.use_cassette(os.path.join(utils.settings.cache,hash.hexdigest())):     
#         for paper in target():
#             paper = pyastroapi.articles.article(data=paper)
#             self.add(paper, callback)


#     def add(self, paper, callback):
#         # Creating the ListStore model
#         pdficon = 'go-down'
#         try:
#             if os.path.exists(os.path.join(utils.settings.pdffolder,paper.pdf.filename())):
#                 pdficon = 'x-office-document'
#         except (ValueError,pyastroapi.api.exceptions.NoRecordsFound,TypeError): # No PDF available
#             pdficon = 'window-close'

#         authors = paper.authors[1:]
#         if len(authors) > 3:
#             authors = authors[0:3]
#             authors.append('et al')
#         authors = '; '.join([i.strip() for i in authors])

#         try:
#             refs = len(paper.references())
#         except pyastroapi.api.exceptions.MalformedRequest:
#             refs = 0

#         self.append([
#             paper.title,
#             paper.first_author,
#             paper.year,
#             authors,
#             paper.pub,
#             str(refs),
#             str(paper.citation_count),
#             pdficon,
#             'edit-copy',
#             paper.bibcode
#         ])

#         self.journal.add_articles([paper])
#         callback(paper)

#         # utils.show_status('Showing {} articles'.format(len(self.journal)))
        

#     def refresh_results(self, widget):
#         query = widget.get_text().lower()
#         journal = []

#         for paper in self.journal:
#             if query in paper.title.lower():
#                 journal.append(paper)
#             elif query in paper.abstract.lower():
#                 journal.append(paper)
#             elif query in paper.authors.lower():
#                 journal.append(paper)
#             elif query in paper.year:
#                 journal.append(paper)

#         self.make(journal)
#         utils.show_status(f"Showing {len(journal)} out of {len(self.journal)}")


# class JournalView(Gtk.TreeModelSort):
#     def __init__(self, notebook, store):
#         Gtk.TreeModelSort.__init__(self, store)

#         self.store = store
#         self.notebook = notebook
#         self.journal = pyastroapi.articles.journal()

#         self.set_sort_func(2, self.int_compare, 2)
#         self.set_sort_func(5, self.int_compare, 5)
#         self.set_sort_func(6, self.int_compare, 6)

#         self.treeview = Gtk.TreeView.new_with_model(self)
#         self.treeview.set_has_tooltip(True)
#         for i, column_title in enumerate(_cols):
#             if column_title in ['PDF','Bibtex']:
#                 renderer = Gtk.CellRendererPixbuf()
#                 column = Gtk.TreeViewColumn(column_title, renderer, icon_name=i)
#                 column.set_expand(False)
#             else:
#                 renderer = Gtk.CellRendererText()
#                 renderer.props.wrap_width = 100
#                 renderer.props.wrap_mode = Gtk.WrapMode.WORD
#                 column = Gtk.TreeViewColumn(column_title, renderer, text=i)
#                 column.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
#                 column.set_resizable(True)
#                 column.set_sort_column_id(i)
#                 if column_title == 'Title':
#                     column.set_expand(True)
#                 if column_title == 'bibcode':
#                     column.set_visible(False)

#             self.treeview.append_column(column)

#         self.treeview.get_column(2).clicked()
#         self.treeview.set_search_column(-1)

#         self.treeview.connect('query-tooltip' , self.tooltip)
#         self.treeview.connect('button-press-event' , self.button_press_event)

#     def set_data(self,paper):
#         self.journal.add_articles([paper])


#     def int_compare(self, model, row1, row2, user_data):
#         value1 = int(model.get_value(row1, user_data))
#         value2 = int(model.get_value(row2, user_data))
#         if value1 > value2:
#             return -1
#         elif value1 == value2:
#             return 0
#         else:
#             return 1

#     def tooltip(self, widget, x, y, keyboard, tooltip):
#         if not len(self.journal):
#             return False
#         try:
#             path = self.treeview.get_path_at_pos(x,y)[0]
#         except TypeError:
#             return True
#         if path is None:
#             return False
#         cp = self.convert_path_to_child_path(path)
#         row = cp.get_indices()[0] 

#         print(row,len(self.journal))
#         if row >= len(self.journal):
#             return
#         if len(self.journal):
#             tooltip.set_text(self.journal[row].abstract)
#             self.treeview.set_tooltip_row(tooltip, path)
#             return True
#         return False

#     def button_press_event(self, treeview, event):
#         try:
#             path,col,_,_ = treeview.get_path_at_pos(int(event.x),int(event.y))
#         except TypeError:
#             return True

#         if path is None:
#             return False

#         cp = self.convert_path_to_child_path(path)
#         row = cp.get_indices()[0] 

#         print(row,len(self.journal))
#         if row >= len(self.journal):
#             return
#         article = self.journal[row]

#         title = col.get_title()
#         if event.button == Gdk.BUTTON_PRIMARY: # left click
#             if title == 'Bibtex':
#                 utils.clipboard(article.bibtex())
#                 utils.show_status(f"Bibtex downloaded for {article.bibcode}")
#             elif title == "First Author":
#                 def func():
#                     return pyastroapi.search.first_author(article.first_author)
#                 JournalPage(func,self.notebook,article.first_author)
#             elif title == 'Citations':
#                 JournalPage(article.citations,self.notebook,'Cites:'+article.name)
#             elif title == 'References':
#                 JournalPage(article.references,self.notebook,'Refs:'+article.name)
#             else:
#                 pdf.ShowPDF(article,self.notebook)
#                 #adsData.db.add_item({article.bibcode:article})
#                 #adsData.db.commit()