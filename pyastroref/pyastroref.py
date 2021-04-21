# SPDX-License-Identifier: GPL-2.0-or-later

import sys,os
import argparse
import threading

from . import adsabs


import gi
gi.require_version("Gtk", "3.0")
gi.require_version('EvinceDocument', '3.0')
gi.require_version('EvinceView', '3.0')
from gi.repository import GLib, Gtk, GObject, Gio, GdkPixbuf, Gdk
from gi.repository import EvinceDocument
from gi.repository import EvinceView


EvinceDocument.init()


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
            OptionsMenu()


    def setup_headerbar(self):
        self.options_menu()

        hb = Gtk.HeaderBar()
        hb.set_show_close_button(True)
        hb.props.title = "pyAstroRef"
        self.set_titlebar(hb)

        hb.pack_end(self.button_opt)

        hb.pack_start(self.search)


    def on_click_load_options(self, button):
        OptionsMenu()

    def options_menu(self):
        self.button_opt = Gtk.Button()
        self.button_opt.connect("clicked", self.on_click_load_options)
        image = Gtk.Image()
        image.set_from_icon_name('open-menu-symbolic', Gtk.IconSize.BUTTON)
        self.button_opt.set_image(image)


    def setup_search_bar(self):
        self.search = Gtk.SearchEntry()
        self.search.set_placeholder_text('Search ADS ...')
        self.search.connect("activate",self.on_click_search)

        self.search.set_can_default(True)
        self.set_default(self.search)
        self.search.set_hexpand(True)

    def on_click_search(self, button):
        query = self.search.get_text()

        if len(query) == 0:
            return

        def target():
            return adsSearch.search(query)

        ShowJournal(target,self.right_panel,query)

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


class OptionsMenu(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="Options")
        self.set_position(Gtk.WindowPosition.CENTER)

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
        self.show_all()   

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


class LeftPanel(object):
    _fields = ['Home', 'ORCID', 'Arxiv', 'Libraries', 'Journals', 'Saved searches']


    def __init__(self, notebook):
        self.store = Gtk.TreeStore(str)
        self.notebook = notebook

        self.rows = {}


        for idx,i in enumerate(self._fields):
            self.rows[i] = {
                            'row': self.store.append(None,[i]),
                            'idx': idx
                            }

        libs = adsdata.libraries.names()
        for i in libs:
            self.store.append(self.rows['Libraries']['row'],[i])

        for i in adsJournals.list_defaults():
            self.store.append(self.rows['Journals']['row'],[adsJournals.default_journals[i]])


        self.tree = Gtk.TreeView(model=self.store)

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("", renderer, text=0)
        self.tree.append_column(column)

        #self.tree.get_selection().connect('changed' , self.row_selected)
        self.tree.connect('button-press-event' , self.button_press_event)


    def button_press_event(self, treeview, event):
        # Get row:
        try:
            path, _,_,_ = treeview.get_path_at_pos(int(event.x),int(event.y))
        except TypeError:
            return True
        if path is None:
            return False

        # path is either a number 0,1,2 etc or 0:1,0:2 for sub-rows of row 0
        if ':' in path.to_string():
            row, child = path.to_string().split(':')
            row = int(row)
            child = list(list(self.store[row].iterchildren())[int(child)])[0]
        else:
            row = int(path.to_string())
            child = None

        target = None
        name = list(self.store[row])[0]
        if event.button == Gdk.BUTTON_PRIMARY: # left click
            if row == self.rows['Home']['idx']:
                def func():
                    return []
                target = func
            elif row == self.rows['Arxiv']['idx']:
                target = adsabs.arxivrss(adsdata.token).articles
            elif row == self.rows['ORCID']['idx']:
                if adsdata.orcid is None:
                    OptionsMenu()
                    return
                def func():
                    return adsSearch.orcid(adsdata.orcid)
                target = func
            elif row == self.rows['Libraries']['idx']:
                # TODO: Refresh data
                pass
            elif row == self.rows['Journals']['idx']:
                # TODO: Refresh data
                pass
            elif row == self.rows['Saved searches']['idx']:
                # TODO: Refresh data
                pass

            if child is not None:
                name = child
                # Must be an item with sub items
                if row == self.rows['Libraries']['idx']:
                    def func():
                        bibcodes = adsdata.libraries[child].keys()
                        return adsSearch.bibcode_multi(bibcodes)
                    target = func
                elif self.rows['Journals']['idx']:
                    def func():
                        return adsJournals.search(child)
                    target = func

                elif self.rows['Saved searches']['idx']:
                    pass

            if target is not None:
                ShowJournal(target,self.notebook,name)  
                return

        elif event.button == Gdk.BUTTON_SECONDARY: # right click
            if row == self.rows['Home']['idx']:
                lpm = LeftPanelMenu(name,child,refresh=True)
            elif row == self.rows['Arxiv']['idx']:
                lpm = LeftPanelMenu(name,child,refresh=True)
            elif row == self.rows['ORCID']['idx']:
                lpm = LeftPanelMenu(name,child,refresh=True)
            elif row == self.rows['Libraries']['idx']:
                lpm = LeftPanelMenu(name,child,add=True,refresh=True)
            elif row == self.rows['Journals']['idx']:
                lpm = LeftPanelMenu(name,child,add=True,refresh=True)
            elif row == self.rows['Saved searches']['idx']:
                lpm = LeftPanelMenu(name,child,add=True,refresh=True)

            if child is not None:
                # Must be an item with sub items
                if row == self.rows['Libraries']['idx']:
                    lpm = LeftPanelMenu(name,child,edit=True,delete=True,refresh=True)
                elif self.rows['Journals']['idx']:
                    lpm = LeftPanelMenu(name,child,edit=True,delete=True,refresh=True)
                elif self.rows['Saved searches']['idx']:
                    lpm = LeftPanelMenu(name,child,edit=True,delete=True,refresh=True)

            lpm.popup_at_pointer(event)


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

        self.header = JournalPopupWindow(self.notebook, self.page, name)


        self.notebook.append_page(self.page, self.header)
        self.notebook.set_tab_reorderable(self.page, True)
        self.notebook.show_all()
        GLib.idle_add(self.header.spin_on)

        self.download()

        self.page.show_all()
        self.notebook.show_all()
        self.header.show_all()


    def download(self):
        def threader():
            self.journal = []
            GLib.idle_add(self.store.clear)
            self.journal = self.target()
            GLib.idle_add(self.make_liststore)
            GLib.idle_add(self.header.spin_off)
            self.header.data = self.journal

        thread = threading.Thread(target=threader)
        thread.daemon = True
        thread.start()

    def make_liststore(self):
        # Creating the ListStore model
        for paper in self.journal:
            pdficon = 'go-down'
            if os.path.exists(paper.filename(True)):
                pdficon = 'x-office-document'

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
                str(paper.reference_count),
                str(paper.citation_count),
                pdficon,
                'edit-copy'
            ])

    def make_treeview(self):
        # creating the treeview and adding the columns
        self.treeviewsorted = Gtk.TreeModelSort(model=self.store)

        self.treeview = Gtk.TreeView.new_with_model(self.treeviewsorted)
        self.treeview.set_has_tooltip(True)
        for i, column_title in enumerate(self.cols):
            if column_title in ['PDF','Bibtex']:
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

        self.treeviewsorted.set_sort_func(2, self.int_compare, 2)
        self.treeviewsorted.set_sort_func(5, self.int_compare, 5)
        self.treeviewsorted.set_sort_func(6, self.int_compare, 6)

        #self.treeview.connect('row-activated' , self.button_press_event)
        self.treeview.connect('query-tooltip' , self.tooltip)
        self.treeview.connect('button-press-event' , self.button_press_event)

    def int_compare(self, model, row1, row2, user_data):
        value1 = int(model.get_value(row1, user_data))
        value2 = int(model.get_value(row2, user_data))
        if value1 > value2:
            return -1
        elif value1 == value2:
            return 0
        else:
            return 1


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
        return False

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
            if title == 'Bibtex':
                clipboard(article.bibtex(text=True))
            elif title == "First Author":
                def func():
                    return adsSearch.first_author(article.first_author)
                ShowJournal(func,self.notebook,q)
            elif title == 'Citations':
                ShowJournal(article.citations,self.notebook,'Cites:'+article.name)
            elif title == 'References':
                ShowJournal(article.references,self.notebook,'Refs:'+article.name)
            else:
                p = ShowPDF(article,self.notebook)
                p.add()


def clipboard(data):
    clip = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
    clip.set_text(data,-1)


class ShowPDF(object):
    def __init__(self, data, notebook):
        self.data = data
        self.notebook = notebook

        self.page = Gtk.ScrolledWindow()
        self.page.astroref_name = self.data.bibcode

        self.header = PDFPopupWindow(self.notebook, self.page, self.data)

        if adsdata.pdffolder is None:
            OptionsMenu()

        self._filename = self.data.filename(True)

    def download(self):
        def get_pdf():
            try:
                self.data.pdf(self._filename)
                GLib.idle_add(self.show)
            except:
                pass

        if not os.path.exists(self._filename):
            thread = threading.Thread(target=get_pdf)
            thread.daemon = True
            thread.start()
        else:
            self.show()
            

    def add(self):
        for p in range(self.notebook.get_n_pages()):
            page = self.notebook.get_nth_page(p)
            if self.data.bibcode == page.astroref_name:
                self.notebook.set_current_page(p)
                self.notebook.show_all()
                return


        self.page_num = self.notebook.append_page(self.page, self.header)
        self.notebook.set_tab_reorderable(self.page, True)
        self.notebook.show_all()

        try:
            self.download()
        except ValueError:
            pass

    def show(self):
        try:
            doc = EvinceDocument.Document.factory_get_document('file://'+self._filename)
        except gi.repository.GLib.Error:
            GLib.idle_add(self.header.spin_off)
            return
        view = EvinceView.View()
        model = EvinceView.DocumentModel()
        model.set_document(doc)
        view.set_model(model)
        self.page.add(view)

        self.page.show_all()
        self.notebook.show_all()
        GLib.idle_add(self.header.spin_off)

class PDFPopupWindow(Gtk.EventBox):
    def __init__(self, notebook, page, data):
        Gtk.EventBox.__init__(self)

        self.notebook = notebook
        self.page = page
        self.data = data

        self.spinner = Gtk.Spinner()
        self.header = Gtk.HBox()
        self.title_label = Gtk.Label(label=self.data.name)
        image = Gtk.Image()
        image.set_from_icon_name('window-close', Gtk.IconSize.MENU)

        self.title_label.set_has_tooltip(True)
        self.title_label.connect('query-tooltip' , self.tooltip)

        self.close_button = Gtk.Button()
        self.close_button.set_image(image)
        self.close_button.set_relief(Gtk.ReliefStyle.NONE)
        self.close_button.connect('clicked', self.on_tab_close)

        GLib.idle_add(self.spin_on)
        self.header.pack_start(self.title_label,
                          expand=True, fill=True, padding=0)
        self.header.pack_end(self.spinner,
                        expand=False, fill=False, padding=0)

        self.header.show_all()

        self.button = {}

        self.popover = Gtk.Popover()

        vbox = Gtk.VBox(orientation=Gtk.Orientation.VERTICAL)

        self.button['open_ads'] = Gtk.LinkButton(uri=self.data.ads_url,label='Open ADS')
        vbox.pack_start(self.button['open_ads'], False, True, 0)

        if len(self.data.arxiv_url):
            self.button['open_arxiv'] = Gtk.LinkButton(uri=self.data.arxiv_url,label='Open Arxiv')
            vbox.pack_start(self.button['open_arxiv'], False, True, 0)

        if len(self.data.journal_url):
            self.button['open_journal'] = Gtk.LinkButton(uri=self.data.journal_url,label='Open '+self.data.journal)
            vbox.pack_start(self.button['open_journal'], False, True, 0)
        vbox.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, True, 10)

        self.button['copy_bibtex'] = Gtk.Button.new_with_label("Copy Bibtex")
        vbox.pack_start(self.button['copy_bibtex'], False, True, 0)

        self.button['cites'] = Gtk.Button.new_with_label("Citations")
        vbox.pack_start(self.button['cites'], False, True, 0)

        self.button['refs'] = Gtk.Button.new_with_label("References")
        vbox.pack_start(self.button['refs'], False, True, 0)

        vbox.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, True, 10)

        self.button['add_lib'] = Gtk.Button.new_with_label("Add to library")
        vbox.pack_start(self.button['add_lib'], False, True, 0)

        self.button['close'] = Gtk.Button.new_with_label("Close")
        vbox.pack_start(self.button['close'], False, True, 0)

        self.button['del'] = Gtk.Button.new_with_label("Delete")
        vbox.pack_start(self.button['del'], False, True, 0)

        vbox.show_all()

        self.popover.add(vbox)
        self.popover.set_position(Gtk.PositionType.BOTTOM)
        
        self.popover.set_relative_to(self.header)

        self.add(self.header)

        self.connect("button-press-event", self.button_press)

        self.button['copy_bibtex'].connect("button-press-event", self.bp_bib)
        self.button['cites'].connect("button-press-event", self.bp_cites)
        self.button['refs'].connect("button-press-event", self.bp_refs)
        self.button['add_lib'].connect("button-press-event", self.bp_add_lib)

        self.button['close'].connect("button-press-event", self.bp_close)
        self.button['del'].connect("button-press-event", self.bp_del)

    def tooltip(self, widget, x, y, keyboard, tooltip):
        tooltip.set_text(self.data.title)
        return True


    def on_tab_close(self, button):
        self.notebook.remove_page(self.notebook.page_num(self.page))

    def button_press(self, widget, event):
        if event.button == Gdk.BUTTON_PRIMARY:
            self.notebook.set_current_page(self.notebook.page_num(self.page))
            return True
        elif event.button == Gdk.BUTTON_SECONDARY:
            #make widget popup
            self.popover.popup()
            return True
        return False

    def spin_on(self):
        self.spinner.start()

    def spin_off(self):
        self.spinner.stop()
        self.header.remove(self.spinner)
        self.header.pack_end(self.close_button,
                        expand=False, fill=False, padding=0)
        self.header.show_all()


    def bp_bib(self, widget, event):
        clipboard(self.data.bibtex(text=True))
        return True

    def bp_cites(self, widget, event):
        ShowJournal(self.data.citations,self.notebook,'Cites:'+self.data.name)
        return True

    def bp_refs(self, widget, event):
        ShowJournal(self.data.references,self.notebook,'Refs:'+self.data.name)
        return True

    def bp_add_lib(self, widget, event):
        Add2Lib([self.data.bibcode])

    def bp_close(self, widget, event):
        self.on_tab_close(widget)

    def bp_del(self, widget, event):
        os.remove(self.data.filename(True))
        self.on_tab_close(widget)



class JournalPopupWindow(Gtk.EventBox):
    def __init__(self, notebook, page, name):
        Gtk.EventBox.__init__(self)

        self.notebook = notebook
        self.page = page
        self.bibcodes = []
        self.query = ''
        self.name = name

        self.spinner = Gtk.Spinner()
        self.header = Gtk.HBox()
        self.title_label = Gtk.Label(label=self.name)
        image = Gtk.Image()
        image.set_from_icon_name('window-close', Gtk.IconSize.MENU)

        self.close_button = Gtk.Button()
        self.close_button.set_image(image)
        self.close_button.set_relief(Gtk.ReliefStyle.NONE)
        self.close_button.connect('clicked', self.on_tab_close)

        GLib.idle_add(self.spin_on)
        self.header.pack_start(self.title_label,
                          expand=True, fill=True, padding=0)
        self.header.pack_end(self.spinner,
                        expand=False, fill=False, padding=0)

        self.header.show_all()

        self.button = {}

        self.popover = Gtk.Popover()

        vbox = Gtk.VBox(orientation=Gtk.Orientation.VERTICAL)

        self.button['copy_bibtex'] = Gtk.Button.new_with_label("Copy Bibtexs")
        vbox.pack_start(self.button['copy_bibtex'], False, True, 0)

        vbox.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, True, 10)

        self.button['add_lib'] = Gtk.Button.new_with_label("Add to library")
        vbox.pack_start(self.button['add_lib'], False, True, 0)

        self.button['save_search'] = Gtk.Button.new_with_label("Save search")
        vbox.pack_start(self.button['save_search'], False, True, 0)

        vbox.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, True, 10)
        self.button['close'] = Gtk.Button.new_with_label("Close")
        vbox.pack_start(self.button['close'], False, True, 0)

        vbox.show_all()

        self.popover.add(vbox)
        self.popover.set_position(Gtk.PositionType.BOTTOM)
        
        self.popover.set_relative_to(self.header)

        self.add(self.header)

        self.connect("button-press-event", self.button_press)

        self.button['copy_bibtex'].connect("button-press-event", self.bp_bib)
        self.button['add_lib'].connect("button-press-event", self.bp_add_lib)
        self.button['save_search'].connect("button-press-event", self.bp_save_search)

        self.button['close'].connect("button-press-event", self.bp_close)


    def on_tab_close(self, button):
        self.notebook.remove_page(self.notebook.page_num(self.page))

    def button_press(self, widget, event):
        if event.button == Gdk.BUTTON_PRIMARY:
            self.notebook.set_current_page(self.notebook.page_num(self.page))
            return True
        elif event.button == Gdk.BUTTON_SECONDARY:
            #make widget popup
            self.popover.popup()
            return True
        return False

    def spin_on(self):
        self.spinner.start()

    def spin_off(self):
        self.spinner.stop()
        self.header.remove(self.spinner)
        self.header.pack_end(self.close_button,
                        expand=False, fill=False, padding=0)
        self.header.show_all()


    def bp_bib(self, widget, event):
        clipboard(self.data.bibtex(text=True))
        return True

    def bp_add_lib(self, widget, event):
        Add2Lib(self.data.bibcodes())
        return True

    def bp_close(self, widget, event):
        self.on_tab_close(widget)

    def bp_save_search(self, widget, event):
        AddSavedSearch(self.page.astroref_name)


class Add2Lib(Gtk.Window):
    def __init__(self, bibcodes=[]):
        Gtk.Window.__init__(self, title="Add to library")

        self.bibcodes = bibcodes

        self.set_border_width(10)
        self.set_position(Gtk.WindowPosition.CENTER)


        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)


        self.combo = Gtk.ComboBoxText()
        libs = adsdata.libraries.names()
        for i in libs:
            self.combo.append_text(i)

        self.combo.set_entry_text_column(0)
        self.combo.set_active(0)

        vbox.pack_start(self.combo, True,True,0)

        save = Gtk.Button(label='Save')
        save.connect('clicked', self.on_save)

        vbox.pack_start(save, True,True,0)

        self.add(vbox)
        self.show_all()

    def on_save(self, button):
        lib = self.combo.get_active_text()
        if lib is not None and len(self.bibcodes):
            print('Saving to ',lib)
            adsdata.libraries[lib].add(self.bibcodes)
        self.destroy()

class AddSavedSearch(Gtk.Window):
    def __init__(self, query=''):
        Gtk.Window.__init__(self, title="Saved search")

        self.query = query

        self.set_border_width(10)
        self.set_position(Gtk.WindowPosition.CENTER)


        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        self.name = Gtk.Entry()
        self.name.set_placeholder_text('Name')
        vbox.pack_start(self.name, True, True, 0)


        self.entry = Gtk.Entry()
        self.entry.set_placeholder_text('Query')
        self.entry.set_text(query)
        vbox.pack_start(self.entry, True, True, 0)

        self.description = Gtk.Entry()
        self.description.set_placeholder_text('Description')
        vbox.pack_start(self.description, True, True, 0)

        save = Gtk.Button(label='Save')
        save.connect('clicked', self.on_save)

        vbox.pack_start(save, True,True,0)

        self.add(vbox)
        self.show_all()

    def on_save(self, button):
        name = self.name.get_text()
        query = self.query
        description = self.name.get_text()
        print('Saving',name,query,description)
        self.destroy()


class LeftPanelMenu(Gtk.Menu):
    def __init__(self,name,child=None,add=False,edit=False,delete=False,refresh=True):
        Gtk.Menu.__init__(self)
        self.name = name
        self.child = child
        print(name,child)

        if add:
            self.add = Gtk.MenuItem(label='Add')
            self.append(self.add)
            self.add.show()
            self.add.connect('activate', self.on_click_add)

        if edit:
            self.edit = Gtk.MenuItem(label='Edit')
            self.append(self.edit)
            self.edit.show()
            self.edit.connect('activate', self.on_click_edit)

        if delete:
            self.delete = Gtk.MenuItem(label='Delete')
            self.append(self.delete)
            self.delete.show()

        if refresh:
            self.refresh = Gtk.MenuItem(label='Refresh')
            self.append(self.refresh)
            self.refresh.show()

        self.show_all()


    def on_click_add(self, button):
        EditLibrary(self.name,add=True)

    def on_click_edit(self, button):
        EditLibrary(self.name,add=False)

class EditLibrary(Gtk.Window):
    def __init__(self, name=None,add=True):

        if add:
            title = 'New library'
        else:
            title = 'Edit library'

        Gtk.Window.__init__(self, title=title)

        self._name = name
        self._description = ''
        self._public=False
        if self._name is not None:
            if self._name in adsdata.libraries:
                self._lib = adsdata.libraries[self._name]
                self._description = self._lib.description
                self._public = self._lib.public


        self.set_border_width(10)
        self.set_position(Gtk.WindowPosition.CENTER)


        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        self.name = Gtk.Entry()
        self.name.set_placeholder_text('Name')
        self.name.set_text(self._name)
        vbox.pack_start(self.name, True, True, 0)

        self.description = Gtk.Entry()
        self.description.set_placeholder_text('Description')
        self.description.set_text(self._description)
        vbox.pack_start(self.description, True, True, 0)


        hbox = Gtk.Box(spacing=6)
        vbox.add(hbox)
        button1 = Gtk.RadioButton.new_with_label_from_widget(None, "Public")
        button2 = Gtk.RadioButton.new_from_widget(button1)
        button2.set_label("Private")

        button1.connect("toggled", self.on_button_toggled, "public")
        button2.connect("toggled", self.on_button_toggled, "private")
        hbox.pack_start(button1, False, False, 0)
        hbox.pack_start(button2, False, False, 0)

        if self._public:
            button1.set_active(True)
        else:
            button2.set_active(True)


        save = Gtk.Button(label='Save')
        save.connect('clicked', self.on_save)

        vbox.pack_start(save, True,True,0)

        self.add(vbox)
        self.show_all()

    def on_button_toggled(self, button, name):
        print(name,button.get_active())



    def on_save(self, button):
        name = self.name.get_text()
        query = self.query
        description = self.name.get_text()
        print('Saving',name,query,description)
        self.destroy()



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





