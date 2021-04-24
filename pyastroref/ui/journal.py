# SPDX-License-Identifier: GPL-2.0-or-later

import os
import sys
import threading

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk, GObject, Gdk

from . import utils, libraries, pdf, saved_search

from ..papers import adsabs as ads

adsData = ads.adsabs()
adsSearch = ads.articles.search(adsData.token)

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

        self.treeview.get_column(2).clicked()

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
                utils.clipboard(article.bibtex(text=True))
            elif title == "First Author":
                def func():
                    return adsSearch.first_author(article.first_author)
                ShowJournal(func,self.notebook,article.first_author)
            elif title == 'Citations':
                ShowJournal(article.citations,self.notebook,'Cites:'+article.name)
            elif title == 'References':
                ShowJournal(article.references,self.notebook,'Refs:'+article.name)
            else:
                p = pdf.ShowPDF(article,self.notebook)
                p.add()


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
        utils.clipboard(self.data.bibtex(text=True))
        return True

    def bp_add_lib(self, widget, event):
        libraries.Add2Lib(self.data.bibcodes())
        return True

    def bp_close(self, widget, event):
        self.on_tab_close(widget)

    def bp_save_search(self, widget, event):
        saved_search.AddSavedSearch(self.page.astroref_name)