# SPDX-License-Identifier: GPL-2.0-or-later

import os
import sys
import threading

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk, GObject, Gdk

from ..papers import adsabs as ads
from ..papers import collection
from ..papers import arxiv

adsData = ads.adsabs()
adsSearch = ads.articles.search(adsData.token)
adsJournals = collection.Collection(adsData.token)


class JournalWindow(Gtk.Window):
    def __init__(self, callback=None):
        Gtk.Window.__init__(self, title='Edit journals')
        self.set_position(Gtk.WindowPosition.CENTER)
        self._callback = callback

        self.vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)

        self.search = Gtk.SearchEntry()
        self.search.connect("changed", self.refresh_results)

        self.vbox.pack_start(self.search, False, False,0)

        self.scroll=Gtk.ScrolledWindow(hexpand=True, vexpand=True)

        self.store = Gtk.ListStore(str, bool)
        self.make_rows()

        self.set_size_request(1200,400)

        self.treeview = Gtk.TreeView(model=self.store)
        renderer_text = Gtk.CellRendererText()
        column_text = Gtk.TreeViewColumn("Journal", renderer_text, text=0)
        self.treeview.append_column(column_text)
        
        column_text.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        column_text.set_expand(False)

        renderer_toggle = Gtk.CellRendererToggle()
        renderer_toggle.connect("toggled", self.on_cell_toggled)

        column_toggle = Gtk.TreeViewColumn("Show", renderer_toggle, active=1)
        self.treeview.append_column(column_toggle)
        self.treeview.set_enable_search(True)
        self.treeview.show()

        self.scroll.add(self.treeview)
        self.scroll.show()

        self.vbox.pack_start(self.scroll, True,True,0)
        self.vbox.show()

        self.add(self.vbox)
        self.show_all()

        self.connect('delete-event', self.on_destroy)

    def on_cell_toggled(self, widget, path):
        name = self.store[path][0]
        state = self.store[path][1]
        # Toggle-off
        if state:
            self.store[path][1] = False
            adsJournals.all_journals[name] = adsJournals.default_journals[name]
            adsJournals.default_journals.pop(name,None)

        # Toggle-on
        else:
            self.store[path][1] = True
            adsJournals.default_journals[name] = adsJournals.all_journals[name]
            adsJournals.all_journals.pop(name,None)

    def refresh_results(self, widget):
        query = self.search.get_text().lower()
        if not len(query):
            pass
        else:
            self.store.clear()
            self.make_rows(query)


    def make_rows(self,query=''):
        def_journals = sorted(adsJournals.list_defaults(), key=str.lower)
        all_journals = sorted(adsJournals.list_all(), key=str.lower)

        for i in def_journals:
            if i.lower().startswith(query):
                self.store.append([i,True])

        for i in all_journals:
            if i.lower().startswith(query):
                self.store.append([i,False])

    def on_destroy(self, widget,*data):
        if self._callback is not None:
            self._callback('')

        adsJournals.save_defaults()
        return False