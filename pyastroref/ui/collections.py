# SPDX-License-Identifier: GPL-2.0-or-later

import os
import sys
import threading
import datetime
import requests
from pathlib import Path

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk, GObject, Gdk

import pyastroapi

from . import utils

class JournalWindow(Gtk.Window):
    def __init__(self, callback=None):

        self.adsJournals = Collection()

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
            self.adsJournals.all_journals[name] = self.adsJournals.default_journals[name]
            self.adsJournals.default_journals.pop(name,None)

        # Toggle-on
        else:
            self.store[path][1] = True
            self.adsJournals.default_journals[name] = self.adsJournals.all_journals[name]
            self.adsJournals.all_journals.pop(name,None)

    def refresh_results(self, widget):
        query = self.search.get_text().lower()
        if not len(query):
            pass
        else:
            self.store.clear()
            self.make_rows(query)


    def make_rows(self,query=''):
        def_journals = sorted(self.adsJournals.list_defaults(), key=str.lower)
        all_journals = sorted(self.adsJournals.list_all(), key=str.lower)

        for i in def_journals:
            if i.lower().startswith(query):
                self.store.append([i,True])

        for i in all_journals:
            if i.lower().startswith(query):
                self.store.append([i,False])

    def on_destroy(self, widget,*data):
        if self._callback is not None:
            self._callback('')

        return False


class Collection:
    _url = 'http://adsabs.harvard.edu/abs_doc/journals1.html'

    _init_default_journals = {
        'Astronomy and Astrophysics':'A&A',
        'The Astrophysical Journal':'ApJ',
        'The Astrophysical Journal Supplement Series':'ApJS',
        'Monthly Notices of the Royal Astronomical Society':'MNRAS',
        'Nature':'Natur',
        'Nature Astronomy':'NatAs',
        'Science':'Sci'
    }

    default_journals = {}

    def __init__(self):
        self.all_journals = {}
        self._data = {}

        self.load_defaults()

        self.update_journals()


    def load_defaults(self):
        if not os.path.exists(utils.settings.journals):
            self.default_journals = self._init_default_journals
        else:
            self.default_journals = self.read_file(utils.settings.journals)


    def if_update_journal(self):
        if not os.path.exists(utils.settings.all_journals):
            return True

        last_week = datetime.date.today() - datetime.timedelta(days=7)
        p = Path(utils.settings.all_journals)
        last_modified = datetime.date.fromtimestamp(p.stat().st_mtime)
        if last_modified < last_week:
            return True

        return False

    def update_journals(self):
        if self.if_update_journal():
            self.make_file()

        self.all_journals = self.read_file(utils.settings.all_journals)
        # Remove default journals
        for k in self.default_journals.keys():
            self.all_journals.pop(k, None)


    def make_file(self):
        r = requests.get(self._url)
        data = r.content.decode().split('\n')
        
        res = {}
        for line in data:
            if line.startswith('<a href="#" onClick='):
                _, journ_short, name = line.split('>')
                journ_short = journ_short.split()[0].strip()
                name = name.strip()
                res[name] = journ_short

        with open(utils.settings.all_journals,'w') as f:
            for key,value in res.items():
                print(key,value,file=f)

    def read_file(self, filename):
        all_journals = {}
        with open(filename,'r') as f:
            for line in f.readlines():
                l = line.split()
                value = l[-1]
                key = ' '.join(l[:-1])
                all_journals[key.strip()] = value.strip()
        return all_journals


    def save_defaults(self):
        with open(self._file,'w') as f:
            for key,value in self.default_journals.items():
                print(key,value,file=f)

    def list_defaults(self):
        return self.default_journals.keys()

    def list_all(self):
        return self.all_journals.keys()

    def search(self, name):
        for value in self.default_journals:
            if value == name:
                break

        if name not in self._data:
            today = datetime.date.today()
            monthago = today - datetime.timedelta(days=31)

            pubdata = "pubdate:["
            pubdata+= str(monthago.year) +"-"+ str(monthago.month).zfill(2)
            pubdata+= ' TO '
            pubdata+= str(today.year) +"-"+ str(today.month).zfill(2)
            pubdata+=']'

            query = 'bibstem:"'+name+'" AND '+pubdata

            self._data[name] = pyastroapi.search.search(query)

        return self._data[name]