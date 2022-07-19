# SPDX-License-Identifier: GPL-2.0-or-later

import os
import sys
import threading
import vcr
import hashlib

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk, GObject, Gdk

from . import utils, libraries, pdf, saved_search

import pyastroapi

class JournalPage(Gtk.VBox):
    def __init__(self, target, notebook, name):
        Gtk.VBox.__init__(self)
        self.has_search_open=False

        self.target = target
        self.notebook = notebook
        self.scroll = Gtk.ScrolledWindow()

        self.store = JournalStore(name)
        self.store_view = JournalView(self.notebook, self.store)
        self.header = JournalMenu(self.notebook, self, name)
        self.setup_sb()

        self.pack_start(self.sb,False,False,0)

        self.add(self.scroll)

        self.astroref_name = name
        self.set_vexpand(True)
        self.set_hexpand(True)
        self.scroll.add(self.store_view.treeview)

        self.notebook.append_page(self, self.header)
        self.notebook.set_tab_reorderable(self, True)
        self.notebook.show_all()

        self.header.spin_on()
        self.download()

        self.show_all() 
        self.scroll.show_all()
        self.notebook.show_all()
        self.header.show_all()

    def download(self):
        def threader():
            self.store.make(self.target)
            self.header.spin_off()
            #GLib.idle_add(self.header.set_data(self.store.journal)
            #GLib.idle_add(self.store_view.set_data(self.store.journal)


        thread = threading.Thread(target=threader)
        thread.daemon = True
        GLib.idle_add(thread.start)

    def setup_sb(self):
        self.sb = Gtk.SearchEntry() 
        self.sb.connect("changed", self.store.refresh_results)
        self.sb.grab_focus_without_selecting()


class JournalMenu(Gtk.EventBox):
    def __init__(self, notebook, page, name):
        Gtk.EventBox.__init__(self)

        self.notebook = notebook
        self.page = page
        self.name = name

        self.data = None

        self.spinner = Gtk.Spinner()
        self.header = Gtk.HBox()
        self.popover = Gtk.Popover()
        self.title_label = Gtk.Label(label=self.name)

        self.setup_close_button()

        self.spin_on()
        self.header.pack_start(self.title_label,
                          expand=True, fill=True, padding=0)
        self.header.pack_end(self.spinner,
                        expand=False, fill=False, padding=0)

        self.setup_buttons()

        self.header.show_all()
        self.show_all()


    def set_data(self, data):
        self.data = data

    def setup_close_button(self):
        self.close_button = Gtk.Button()
        image = Gtk.Image()
        image.set_from_icon_name('window-close', Gtk.IconSize.MENU)
        self.close_button.set_image(image)
        self.close_button.set_relief(Gtk.ReliefStyle.NONE)
        self.close_button.connect('clicked', self.on_tab_close)

    def setup_buttons(self):
        self.button = {}

        self.vbox = Gtk.VBox(orientation=Gtk.Orientation.VERTICAL)

        buttons = ['copy_bibtex','add_lib','save_search','close']
        labels = ["Copy BibTex","Add all to library","Save search","Close"]
        seps = [True, False, True, False, False]
        actions = [self.bp_bib,self.bp_add_lib,self.bp_save_search,self.bp_close]

        for button, label, action,sep in zip(buttons, labels, actions, seps):
            self.button[button] = Gtk.Button.new_with_label(label)
            self.vbox.pack_start(self.button[button], False, True, 0)
            self.button[button].connect('button-press-event', action)
            if sep:
                self.vbox.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, True, 10)

        self.vbox.show_all()

        self.popover.add(self.vbox)
        self.popover.set_position(Gtk.PositionType.BOTTOM)
        
        self.popover.set_relative_to(self.header)

        self.add(self.header)

        self.connect("button-press-event", self.button_press)


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
        if self.data is not None:
            utils.clipboard(self.data.bibtex())
            utils.show_status("Bibtex downloaded")
        return True

    def bp_add_lib(self, widget, event):
        if self.data is not None:
            libraries.Add2Lib(self.data.bibcodes())
        return True

    def bp_close(self, widget, event):
        self.on_tab_close(widget)

    def bp_save_search(self, widget, event):
        saved_search.AddSavedSearch(self.page.astroref_name)


_cols = ["Title", "First Author", "Year", "Authors", "Journal","References", "Citations", 
        "PDF", "Bibtex","bibcode"]

class JournalStore(Gtk.ListStore):
    def __init__(self, name):
        Gtk.ListStore.__init__(self, *[str]*len(_cols))
        self.journal = []
        self.name = name
        self.clear()

    def make(self, target):
        hash = hashlib.sha256()
        hash.update(self.name.encode())
        #with vcr.use_cassette(os.path.join(utils.settings.cache,hash.hexdigest())):     
        for paper in target():
            print(paper)
            paper = pyastroapi.articles.article(data=paper)
            self.add(paper)


    def add(self, paper):
        # Creating the ListStore model
        pdficon = 'go-down'
        try:
            if os.path.exists(os.path.join(utils.settings.pdffolder,paper.pdf.filename())):
                pdficon = 'x-office-document'
        except (ValueError,pyastroapi.api.exceptions.NoRecordsFound,TypeError): # No PDF available
            pdficon = 'window-close'

        authors = paper.authors()[1:]
        if len(authors) > 3:
            authors = authors[0:3]
            authors.append('et al')
        authors = '; '.join([i.strip() for i in authors])

        try:
            refs = len(paper.references())
        except pyastroapi.api.exceptions.MalformedRequest:
            refs = 0

        self.append([
            paper.title[0],
            paper.first_author(),
            paper.year,
            authors,
            paper.pub,
            str(refs),
            str(paper.citation_count),
            pdficon,
            'edit-copy',
            paper.bibcode
        ])

        # utils.show_status('Showing {} articles'.format(len(self.journal)))
        

    def refresh_results(self, widget):
        query = widget.get_text().lower()
        journal = []

        for paper in self.journal:
            if query in paper.title.lower():
                journal.append(paper)
            elif query in paper.abstract.lower():
                journal.append(paper)
            elif query in paper.authors.lower():
                journal.append(paper)
            elif query in paper.year:
                journal.append(paper)

        self.make(journal)
        utils.show_status(f"Showing {len(journal)} out of {len(self.journal)}")


class JournalView(Gtk.TreeModelSort):
    def __init__(self, notebook, store):
        Gtk.TreeModelSort.__init__(self, store)

        self.store = store
        self.notebook = notebook
        self.journal = []

        self.set_sort_func(2, self.int_compare, 2)
        self.set_sort_func(5, self.int_compare, 5)
        self.set_sort_func(6, self.int_compare, 6)

        self.treeview = Gtk.TreeView.new_with_model(self)
        self.treeview.set_has_tooltip(True)
        for i, column_title in enumerate(_cols):
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
                if column_title == 'bibcode':
                    column.set_visible(False)

            self.treeview.append_column(column)

        self.treeview.get_column(2).clicked()
        self.treeview.set_search_column(-1)

        self.treeview.connect('query-tooltip' , self.tooltip)
        self.treeview.connect('button-press-event' , self.button_press_event)

    def set_data(self,journal):
        print("Called",journal)
        self.journal = journal


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
        cp = self.convert_path_to_child_path(path)
        row = cp.get_indices()[0] 
        if len(self.journal):
            tooltip.set_text(self.journal[row].abstract)
            self.treeview.set_tooltip_row(tooltip, path)
            return True
        return False

    def button_press_event(self, treeview, event):
        try:
            path,col,_,_ = treeview.get_path_at_pos(int(event.x),int(event.y))
        except TypeError:
            return True

        if path is None:
            return False

        cp = self.convert_path_to_child_path(path)
        row = cp.get_indices()[0] 

        article = self.journal[row]

        title = col.get_title()
        if event.button == Gdk.BUTTON_PRIMARY: # left click
            if title == 'Bibtex':
                utils.clipboard(article.bibtex())
                utils.show_status(f"Bibtex downloaded for {article.bibcode}")
            elif title == "First Author":
                def func():
                    return pyastroapi.search.first_author(article.first_author)
                JournalPage(func,self.notebook,article.first_author)
            elif title == 'Citations':
                JournalPage(article.citations,self.notebook,'Cites:'+article.name)
            elif title == 'References':
                JournalPage(article.references,self.notebook,'Refs:'+article.name)
            else:
                pdf.ShowPDF(article,self.notebook)
                #adsData.db.add_item({article.bibcode:article})
                #adsData.db.commit()