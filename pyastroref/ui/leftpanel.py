# SPDX-License-Identifier: GPL-2.0-or-later

import os
import sys
import threading

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk, GObject, Gdk

from . import results, utils, saved_search, libraries

import pyastroapi.articles as articles
import pyastroapi.search as search
import pyastroapi

from . import shelves

class LeftPanel(object):
    _fields = ['Home', 'ORCID', 'Arxiv', 'Libraries', 'Journals', 'Saved searches']


    def __init__(self, notebook):
        self.store = Gtk.TreeStore(str)
        self.notebook = notebook

        self.libs = pyastroapi.libraries.libraries()
        self.adsJournals = shelves.Shelf()

        self.make_rows()

        self.treeview = Gtk.TreeView(model=self.store)

        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("", renderer, text=0)
        self.treeview.append_column(column)

        self.treeview.set_has_tooltip(True)
        self.treeview.connect('query-tooltip' , self.tooltip)

        self.treeview.connect('button-press-event' , self.button_press_event)
        self.treeview.set_search_column(-1)

    def make_rows(self):
        self.rows = {}
        for idx,i in enumerate(self._fields):
            self.rows[i] = {
                            'row': self.store.append(None,[i]),
                            'idx': idx
                            }

        libs = sorted(self.libs.names(),key=str.lower)
        for i in libs:
            self.store.append(self.rows['Libraries']['row'],[i])

        show_journals = sorted([self.adsJournals.default_journals[i] for i in self.adsJournals.list_defaults()],key=str.lower)
        for i in show_journals:
            self.store.append(self.rows['Journals']['row'],[i])


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
                pass
                #target = arxiv.arxivrss(adsData).articles
            elif row == self.rows['ORCID']['idx']:
                if utils.settings.orcid is None:
                    utils.orcid_error_window()
                    return
                def func():
                    return articles.journal(data=search.orcid(utils.settings.orcid))
                target = func
            elif row == self.rows['Libraries']['idx']:
                pass
            elif row == self.rows['Journals']['idx']:
                pass
            elif row == self.rows['Saved searches']['idx']:
                pass

            if child is not None:
                name = child
                # Must be an item with sub items
                if row == self.rows['Libraries']['idx']:
                    def func():
                        bibcodes = self.libs[child].keys()
                        return articles.journal(bibcodes=bibcodes)
                        #return adsSearch.bibcode_multi(bibcodes)
                    target = func
                elif self.rows['Journals']['idx']:
                    def func():
                        return
                        #return adsJournals.search(child)
                    target = func

                elif self.rows['Saved searches']['idx']:
                    pass

            if target is not None:
                results.ResultsPage(target,self.notebook,name)  
                return

        elif event.button == Gdk.BUTTON_SECONDARY: # right click
            if row == self.rows['Home']['idx']:
                lpm = LeftPanelMenu(name,child,refresh=True)
            elif row == self.rows['Arxiv']['idx']:
                lpm = LeftPanelMenu(name,child,refresh=True)
            elif row == self.rows['ORCID']['idx']:
                lpm = LeftPanelMenu(name,child,refresh=True)
            elif row == self.rows['Libraries']['idx']:
                lpm = LeftPanelMenu(name,child,add=True,refresh=True,
                                    refresh_callback=self.up_alllibs)
            elif row == self.rows['Journals']['idx']:
                lpm = LeftPanelMenu(name,child,add=True,refresh=True,
                                    refresh_callback=self.up_alllibs)
            elif row == self.rows['Saved searches']['idx']:
                lpm = LeftPanelMenu(name,child,add=True,refresh=True,
                                    refresh_callback=self.up_alllibs)

            if child is not None:
                # Must be an item with sub items
                if row == self.rows['Libraries']['idx']:
                    lpm = LeftPanelMenu(name,child,edit=True,delete=True,refresh=True,
                                        refresh_callback=self.up_alllibs)
                elif self.rows['Journals']['idx']:
                    lpm=None
                    pass
                    #lpm = LeftPanelMenu(name,child,edit=True,delete=True,refresh=True)
                elif self.rows['Saved searches']['idx']:
                    lpm = LeftPanelMenu(name,child,edit=True,delete=True,refresh=True)

            if lpm is not None:
                lpm.popup_at_pointer(event)

    def up_alllibs(self, name):
        self.store.clear()
        GLib.idle_add(self.make_rows)

    def tooltip(self, widget, x, y, keyboard, tooltip):
        # Get row:
        try:
            path, _,_,_ = self.treeview.get_path_at_pos(x,y)
        except TypeError:
            return False
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
        name = list(self.store[row])[0]

        if name=='Journals' and child is not None:
            for key,value in self.adsJournals.default_journals.items():
                if value == child:
                    name=key

            tooltip.set_text(name)
            self.treeview.set_tooltip_row(tooltip, path)
            return True
            
        if name=='Libraries' and child is not None:
            tooltip.set_text(self.libs.libraries[child].description)
            self.treeview.set_tooltip_row(tooltip, path)
            return True

        return False


class LeftPanelMenu(Gtk.Menu):
    def __init__(self,name,child=None,add=False,edit=False,delete=False,refresh=True,
                refresh_callback=None):
        Gtk.Menu.__init__(self)
        self.name = name
        self.child = child
        self.refresh_callback = refresh_callback

        self.libs = pyastroapi.libraries.libraries()

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
            self.delete.connect('activate', self.on_click_delete)

        if refresh:
            self.refresh = Gtk.MenuItem(label='Refresh')
            self.append(self.refresh)
            self.refresh.show()
            self.refresh.connect('activate', self.on_click_refresh)

        self.show_all()


    def on_click_add(self, button):
        if self.name == 'Journals':
            shelf.JournalWindow(callback=self.refresh_callback)
        else:
            libraries.EditLibrary(None,add=True, callback=self.refresh_callback)

    def on_click_edit(self, button):
        name = self.name
        if self.child is not None:
            name=self.child
        libraries.EditLibrary(name,add=False, callback=self.refresh_callback)

    def on_click_delete(self, button):
        name = self.name
        if self.child is not None:
            name=self.child
        self.libs.remove(name)
        if self.refresh_callback is not None:
            self.refresh_callback(name)

    def on_click_refresh(self, button):
        name = self.name
        if self.child is not None:
            name=self.child
        if self.refresh_callback is not None:
            self.refresh_callback(name)