# SPDX-License-Identifier: GPL-2.0-or-later

import os
import sys
import threading

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk, GObject, Gdk

from . import utils, libraries, pdf, saved_search

import pyastroapi

class ShowJournal(Gtk.VBox):
    cols = ["Title", "First Author", "Year", "Authors", "Journal","References", "Citations", 
            "PDF", "Bibtex","bibcode"]
    def __init__(self, target, notebook, name):
        Gtk.VBox.__init__(self)
        self.has_search_open=False

        self.target = target
        self.notebook = notebook

        self.store = Gtk.ListStore(*[str]*len(self.cols))
        self.journal = []
        self._journal = []
        self.make_liststore(self._journal)
        self.make_treeview()

        self.sb = Gtk.SearchEntry() 
        self.pack_start(self.sb,False,False,0)
        self.sb.connect("changed", self.refresh_results)    
        self.sb.grab_focus_without_selecting()

        self.scroll = Gtk.ScrolledWindow()
        self.add(self.scroll)

        self.astroref_name = name
        self.set_vexpand(True)
        self.set_hexpand(True)
        self.scroll.add(self.treeview)

        self.header = JournalPopupWindow(self.notebook, self, name)


        self.notebook.append_page(self, self.header)
        self.notebook.set_tab_reorderable(self, True)
        self.notebook.show_all()
        GLib.idle_add(self.header.spin_on)

        self.download()

        self.show_all() 
        self.scroll.show_all()
        self.notebook.show_all()
        self.header.show_all()

    def download(self):
        def threader():
            self._journal = []
            GLib.idle_add(self.store.clear)
            try:
                self._journal = self.target()
            except Exception:
                GLib.idle_add(utils.ads_error_window)

            GLib.idle_add(self.make_liststore,self._journal)
            GLib.idle_add(self.header.spin_off)
            self.header.data = self._journal

        thread = threading.Thread(target=threader)
        thread.daemon = True
        thread.start()

    def make_liststore(self,journal):
        self.store.clear()
        # Creating the ListStore model
        for paper in journal:
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
                'edit-copy',
                paper.bibcode
            ])

        self.journal = journal
        utils.show_status('Showing {} articles'.format(len(self.journal)))



    def make_treeviewsort(self):
        self.treeviewsorted = Gtk.TreeModelSort(model=self.store)
        self.treeviewsorted.set_sort_func(2, self.int_compare, 2)
        self.treeviewsorted.set_sort_func(5, self.int_compare, 5)
        self.treeviewsorted.set_sort_func(6, self.int_compare, 6)

    def make_treeview(self):
        # creating the treeview and adding the columns
        self.make_treeviewsort()
        
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
                if column_title == 'bibcode':
                    column.set_visible(False)

            self.treeview.append_column(column)

        self.treeview.get_column(2).clicked()
        self.treeview.set_search_column(-1)

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
            path,col,_,_ = treeview.get_path_at_pos(int(event.x),int(event.y))
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
                utils.clipboard(article.bibtex())
                utils.show_status('Bibtex downloaded for {}'.format(article.bibcode))
            elif title == "First Author":
                def func():
                    return pyastroapi.search.first_author(article.first_author)
                ShowJournal(func,self.notebook,article.first_author)
            elif title == 'Citations':
                ShowJournal(article.citations,self.notebook,'Cites:'+article.name)
            elif title == 'References':
                ShowJournal(article.references,self.notebook,'Refs:'+article.name)
            else:
                pdf.ShowPDF(article,self.notebook)
                #adsData.db.add_item({article.bibcode:article})
                #adsData.db.commit()


    def refresh_results(self, widget):
        query = widget.get_text().lower()
        journal = []
        if len(self._journal) == 0 or len(self.journal) ==0:
            return
        
        for paper in self._journal:
            if query in paper.title.lower():
                journal.append(paper)
            elif query in paper.abstract.lower():
                journal.append(paper)
            elif query in paper.authors.lower():
                journal.append(paper)
            elif query in paper.year:
                journal.append(paper)

        self.make_liststore(journal)
        utils.show_status('Showing {} out of {}'.format(len(journal),len(self._journal)))


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
        utils.clipboard(self.data.bibtex())
        utils.show_status('Bibtex downloaded for {}'.format(self.data.bibcode))
        return True

    def bp_add_lib(self, widget, event):
        libraries.Add2Lib(self.data.bibcodes())
        return True

    def bp_close(self, widget, event):
        self.on_tab_close(widget)

    def bp_save_search(self, widget, event):
        saved_search.AddSavedSearch(self.page.astroref_name)