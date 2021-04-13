# SPDX-License-Identifier: GPL-2.0-or-later

import sys,os
import argparse
import threading
from enum import Enum

from . import adsabs


import gi
gi.require_version("Gtk", "3.0")
gi.require_version('EvinceDocument', '3.0')
gi.require_version('EvinceView', '3.0')
from gi.repository import GLib, Gtk, GObject, Gio, GdkPixbuf, Gdk
from gi.repository import EvinceDocument
from gi.repository import EvinceView


EvinceDocument.init()


class ERRORS(Enum):
    DOWNLOAD = 1
    PDF = 2

adsdata=adsabs.adsabs()

adsSearch = adsabs.search(adsdata.token)
adsJournals = adsabs.JournalData(adsdata.token)


class MainWindow(Gtk.Window):
    def __init__(self):
        self._init = False
        self.settings = {}
        self.pages = {}

        Gtk.Window.__init__(self, title="pyAstroRef")


        self.setup_search_bar()
        self.setup_headerbar()
        self.setup_panels()

        self.setup_grid()  

        if adsdata.token is None:
            ShowOptionsMenu()


    def setup_headerbar(self):
        self.options_menu()

        hb = Gtk.HeaderBar()
        hb.set_show_close_button(True)
        hb.props.title = "pyAstroRef"
        self.set_titlebar(hb)

        hb.pack_end(self.button_opt)

        hb.pack_start(self.search)


    def on_click_load_options(self, button):
        ShowOptionsMenu()

    def options_menu(self):
        self.button_opt = Gtk.Button()
        self.button_opt.connect("clicked", self.on_click_load_options)
        image = Gtk.Image()
        image.set_from_icon_name('open-menu-symbolic', Gtk.IconSize.BUTTON)
        self.button_opt.set_image(image)


    def setup_search_bar(self):
        self.search = Gtk.SearchEntry()
        #self.search.set_width_chars(100)
        self.search.set_placeholder_text('Search ADS ...')
        self.search.connect("activate",self.on_click_search)

        self.search.set_can_default(True)
        self.set_default(self.search)
        self.search.set_hexpand(True)

    def on_click_search(self, button):
        query = self.search.get_text()

        if len(query) == 0:
            return

        Search(query, self.right_panel)

    def setup_panels(self):
        self.panels = Gtk.HPaned()

        self.right_panel = Gtk.Notebook(scrollable=True)
        self.right_panel.set_vexpand(True)
        self.right_panel.set_hexpand(True)

        self.left_panel = LeftPanel(self.right_panel)
        def func():
            return []
        ShowJournal(func,self.right_panel, 'Home')
        
        self.right_panel.show_all()

        self.panels.pack1(self.left_panel.tree,False,False)
        self.panels.pack2(self.right_panel,True,True)


    def setup_grid(self):
        self.grid = Gtk.Grid()
        self.grid.set_orientation(Gtk.Orientation.VERTICAL)

        self.add(self.grid)

        self.grid.add(self.panels)


def ShowOptionsMenu():
    win = OptionsMenu()
    win.set_position(Gtk.WindowPosition.CENTER)
    win.show_all()


class OptionsMenu(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="Options")

        grid = Gtk.Grid()
        self.add(grid)

        self.ads_entry = Gtk.Entry()
        self.ads_entry.set_width_chars(50)

        if adsdata.token is not None:
            self.ads_entry.set_text(adsdata.token)

        self.orcid_entry = Gtk.Entry()
        if adsdata.orcid is not None:
            self.orcid_entry.set_text(adsdata.orcid)
        self.orcid_entry.set_width_chars(50)

        label = "Choose Folder"
        if adsdata.pdffolder is not None:
            label = adsdata.pdffolder

        self.folder_entry = Gtk.Button(label=label)
        self.folder_entry.connect("clicked", self.on_file_clicked)

        ads_label = Gtk.Label()

        ads_label.set_markup("<a href=\"https://ui.adsabs.harvard.edu/user/settings/token\">"
                            "ADSABS ID</a>")
        
        
        orcid_label = Gtk.Label()
        orcid_label.set_markup("<a href=\"https://orcid.org/\">"
                            "ORCID</a>")

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
        adsdata.token = value

    def save_orcid(self, button):
        value = self.orcid_entry.get_text()
        adsdata.orcid = value  

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
            adsdata.pdffolder = f
            
        dialog.destroy()


        #x = adsabs.arxivrss(adsdata.token)
        #label = Gtk.Label('Arxiv')
        #self.right_panel.append_page(ShowJournal(x.articles(),self.right_panel).add(),label)


class LeftPanel(object):
    def __init__(self, notebook):
        self.store = Gtk.TreeStore(str)
        self.notebook = notebook

        self.store.append(None,['Home'])
        self.store.append(None,['ORCID'])
        self.store.append(None,['Arxiv'])
        self._lib = self.store.append(None,['Libraries'])

        self._journal = self.store.append(None,['Journals'])
        for i in adsJournals.list_defaults():
            self.store.append(self._journal,[adsJournals.default_journals[i]])


        self._search = self.store.append(None,['Saved searches'])


        self.tree = Gtk.TreeView(model=self.store)

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("", renderer, text=0)
        self.tree.append_column(column)

        self.tree.get_selection().connect('changed' , self.row_selected)

    def row_selected(self, selection):
        model, iters = selection.get_selected()

        row = model[iters][0]
        parent = None
        if model[iters].parent is not None:
            parent = model[iters].parent[0]

        for p in range(self.notebook.get_n_pages()):
            page = self.notebook.get_nth_page(p)
            if row == page.astroref_name:
                self.notebook.set_current_page(p)
                self.notebook.show_all()
                return

        target = None       
        if row == 'Home':
            def func():
                return []
            target = func
        elif row == 'Arxiv':
            target = adsabs.arxivrss(adsdata.token).articles
        elif row == 'ORCID':
            if adsdata.orcid is None:
                ShowOptionsMenu()
                return

            def func():
                return adsdata.search('orcid:"'+str(adsdata.orcid) +'"')
            target = func
        elif parent is not None:
            if parent == 'Libraries':
                def func():
                    print(len(adsdata.libraries[row].keys()))
                    bibcodes = adsdata.libraries[row].keys()
                    return adsabs.chunked_search(adsdata.token,bibcodes,'bibcode:')
                target = func
            elif parent == 'Journals':
                def func():
                    return adsJournals.search(row)
                target = func

        if target is not None:
            ShowJournal(target,self.notebook,row)  
            return

        # Things that need thier data fetching when we expand thier row

        if row == 'Libraries':
            libs = adsdata.libraries.names()
            for i in libs:
                self.store.append(self._lib,[i])


    #connect('row_expanded')



class Search(object):
    def __init__(self, query, notebook):
        self._query = query
        self.notebook = notebook

        def target():
            return adsdata.search(query)

        ShowJournal(target,self.notebook,query)  


class ShowJournal(object):
    cols = ["Title", "First Author", "Year", "Authors", "Journal","References", "Citations", "PDF", "Bibtex"]
    def __init__(self, target, notebook, name):
        self.target = target
        self.notebook = notebook

        self.store = Gtk.ListStore(*[str]*len(self.cols))
        self.journal = []
        self.make_liststore()
        self.make_treeview()

        # setting up the layout, putting the treeview in a scrollwindow
        self.page = Gtk.ScrolledWindow()
        self.page.astroref_name = name
        self.page.set_vexpand(True)
        self.page.set_hexpand(True)
        self.page.add(self.treeview)

        self.header = Gtk.HBox()
        title_label = Gtk.Label(name)
        image = Gtk.Image()
        image.set_from_stock(Gtk.STOCK_CLOSE, Gtk.IconSize.MENU)

        self.close_button = Gtk.Button()
        self.close_button.set_image(image)
        self.close_button.set_relief(Gtk.ReliefStyle.NONE)
        self.close_button.connect('clicked', self.on_tab_close)

        self.menu = Gtk.Menu()
        menuitem = Gtk.MenuItem("Test1")
        self.menu.append(menuitem)
        menuitem.show()
        menuitem = Gtk.MenuItem("Test2")
        menuitem.show()
        self.menu.append(menuitem)

        self.header.connect_object('event', self.on_pop_menu, self.menu)

        self.spinner = Gtk.Spinner()

        self.header.pack_start(title_label,
                          expand=True, fill=True, padding=0)
        self.header.pack_end(self.spinner,
                        expand=False, fill=False, padding=0)
        self.spinner.start()    
        self.header.show_all()


        self.notebook.append_page(self.page, self.header)
        self.notebook.set_tab_reorderable(self.page, True)
        self.notebook.show_all()

        self.download()

        self.page.show_all()
        self.notebook.show_all()
        self.spinner.stop()
        self.header.remove(self.spinner)
        self.header.pack_end(self.close_button,
                        expand=False, fill=False, padding=0)
        self.header.show_all()


    def on_pop_menu(self, widget, event):
        print('Right click a')
        if event.type == Gdk.BUTTON_PRESS and event.button == Gdk.BUTTON_SECONDARY:
            print('Right click?')
            widget.popup(None, None, None, None, event.button, event.time)


    def download(self):
        def threader():
            journal = self.target()
            GLib.idle_add(self.store.clear)
            self.journal = journal
            GLib.idle_add(self.make_liststore)

        print('Start downloading data')
        thread = ThreadWithResult(target=threader)
        thread.daemon = True
        thread.start()
        #thread.join()
        print('End downloading data')

    def make_liststore(self):
        # Creating the ListStore model
        for paper in self.journal:

            pdficon = 'go-down'
            #if os.path.exists(os.path.join(adsdata._pdffolder,paper.filename)):
            #    pdficon = 'x-office-document'

            authors = paper.authors.split(';')[1:]
            if len(authors) > 3:
                authors = authors[0:3]
                authors.append('et al')
            authors = '; '.join([i.strip() for i in authors])

            self.store.append([
                paper.title,
                paper.first_author,
                paper.year,
                authors,
                paper.journal,
                'go-down',
                'go-down',
                pdficon,
                'edit-copy'
            ])

    def make_treeview(self):
        # creating the treeview and adding the columns
        self.treeviewsorted = Gtk.TreeModelSort(model=self.store)

        self.treeview = Gtk.TreeView.new_with_model(self.treeviewsorted)
        self.treeview.set_has_tooltip(True)
        for i, column_title in enumerate(self.cols):
            if column_title in ['PDF','Bibtex','Citations','References']:
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

        #self.treeview.connect('row-activated' , self.button_press_event)
        self.treeview.connect('query-tooltip' , self.tooltip)
        self.treeview.connect('button-press-event' , self.button_press_event)

    def tooltip(self, widget, x, y, keyboard, tooltip):
        if not len(self.journal):
            return False
        try:
            path = self.treeview.get_path_at_pos(x,y)[0]
        except TypeError:
            return True
        if path is None:
            return False
        cp = self.treeviewsorted.convert_path_to_child_path(path)
        row = cp.get_indices()[0] 
        if len(self.journal):
            tooltip.set_text(self.journal[row].abstract)
            self.treeview.set_tooltip_row(tooltip, path)
        return True

    def button_press_event(self, treeview, event):
        try:
            path,col,_,_ = self.treeview.get_path_at_pos(int(event.x),int(event.y))
        except TypeError:
            return True

        if path is None:
            return False
        cp = self.treeviewsorted.convert_path_to_child_path(path)
        row = cp.get_indices()[0] 
        article = self.journal[row]

        title = col.get_title()
        if event.button == Gdk.BUTTON_PRIMARY: # left click
            print('Here')
            if title == 'Bibtex':
                clipboard(article.bibtex(text=True))
            elif title == "First Author":
                q = 'author:"^'+article.first_author+'"'
                def func():
                    return adsSearch.search(q)
                ShowJournal(func,self.notebook,q)
            elif title == 'Citations':
                ShowJournal(article.citations,self.notebook,'Cites:'+article.name)
            elif title == 'References':
                ShowJournal(article.references,self.notebook,'Refs:'+article.name)
            else:
                print('Show...')
                p = ShowPDF(article,self.notebook)
                p.add()


    def on_tab_close(self, button):
        self.notebook.remove_page(self.notebook.page_num(self.page))



def clipboard(data):
    clip = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
    clip.set_text(data,-1)


class ShowPDF(object):
    def __init__(self, data, notebook):
        self.data = data
        self.notebook = notebook
        self.spinner = Gtk.Spinner()
        self.header = Gtk.HBox()


        if adsdata.pdffolder is None:
            ShowOptionsMenu()

        self._filename = os.path.join(adsdata.pdffolder,self.data.filename)

    def download(self):
        def get_pdf():
            try:
                self.data.pdf(self._filename)
                GLib.idle_add(self.show)
            except:
                pass
            GLib.idle_add(self.stop_spiner)

        if not os.path.exists(self._filename):
            thread = threading.Thread(target=get_pdf)
            thread.daemon = True
            thread.start()
        else:
            self.show()
            self.stop_spiner()
            

    def add(self):
        print('Start',self._filename)

        for p in range(self.notebook.get_n_pages()):
            page = self.notebook.get_nth_page(p)
            if self.data.bibcode == page.astroref_name:
                self.notebook.set_current_page(p)
                self.notebook.show_all()
                self.stop_spiner()
                return

        self.page = Gtk.ScrolledWindow()
        self.page.astroref_name = self.data.bibcode

        title_label = Gtk.Label(self.data.name)
        image = Gtk.Image()
        image.set_from_stock(Gtk.STOCK_CLOSE, Gtk.IconSize.MENU)

        title_label.set_has_tooltip(True)
        title_label.connect('query-tooltip' , self.tooltip)

        self.close_button = Gtk.Button()
        self.close_button.set_image(image)
        self.close_button.set_relief(Gtk.ReliefStyle.NONE)
        self.close_button.connect('clicked', self.on_tab_close)

        self.header.pack_start(title_label,
                          expand=True, fill=True, padding=0)
        self.header.pack_end(self.spinner,
                        expand=False, fill=False, padding=0)
        self.spinner.start()    
        self.header.show_all()


        self.page_num = self.notebook.append_page(self.page, self.header)
        self.notebook.set_tab_reorderable(self.page, True)
        self.notebook.show_all()

        try:
            self.download()
        except ValueError:
            pass


    def tooltip(self, widget, x, y, keyboard, tooltip):
        tooltip.set_text(self.data.title)

        return True


    def show(self):
        print('Start show')
        try:
            doc = EvinceDocument.Document.factory_get_document('file://'+self._filename)
        except gi.repository.GLib.Error:
            #ErrorWindow(self.data,ERRORS.PDF)
            return
        view = EvinceView.View()
        model = EvinceView.DocumentModel()
        model.set_document(doc)
        view.set_model(model)
        self.page.add(view)

        self.page.show_all()
        self.notebook.show_all()


    def stop_spiner(self):
        self.spinner.stop()
        self.header.remove(self.spinner)
        self.header.pack_end(self.close_button,
                        expand=False, fill=False, padding=0)
        self.header.show_all()


    def on_tab_close(self, button):
        self.notebook.remove_page(self.notebook.page_num(self.page))


class ErrorWindow(Gtk.Window):
    def __init__(self, data, ERROR_CODE):
        self.data= data
        self.ERROR_CODE=ERROR_CODE

        text_2 = ''
        if self.ERROR_CODE == ERRORS.DOWNLOAD:
            text_1 = 'Could not download '+self.data.bibcode
        elif self.ERROR_CODE == ERRORS.PDF:
            text_1 = 'Not a valid pdf file for '+self.data.bibcode
            text_2 = os.path.join(adsdata.pdffolder,self.data.filename)

        dialog = Gtk.MessageDialog(
            transient_for=self,
            flags=0,
            message_type=Gtk.MessageType.INFO,
            buttons=Gtk.ButtonsType.OK,
            text=text_1,
        )
        dialog.format_secondary_text(text_2)
        dialog.run()
        self.add(dialog)
        
        self.show_all() 
        dialog.destroy()

class ThreadWithResult(threading.Thread):
    def __init__(self, group=None, target=None, name=None, args=(), kwargs={}, *, daemon=None):
        def function():
            self.result = target(*args, **kwargs)
        super().__init__(group=group, target=function, name=name, daemon=daemon)




def main():
    win = MainWindow()
    win.connect("destroy", Gtk.main_quit)
    win.set_hide_titlebar_when_maximized(False)
    win.set_position(Gtk.WindowPosition.CENTER)
    win.maximize()
    win.show_all()
    Gtk.main()

def commandline():
    parser = argparse.ArgumentParser()
    args = parser.parse_args()

if __name__ == "__main__":
    commandline()
    main()





