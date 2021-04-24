# SPDX-License-Identifier: GPL-2.0-or-later

import os
import sys
import threading

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk, GObject, Gdk

from . import options, journal, leftpanel, utils


from ..papers import adsabs as ads
from ..papers import articles

adsData = ads.adsabs()
adsSearch = ads.articles.search(adsData.token)


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

        if adsData.token is None:
            options.OptionsMenu()

    def setup_headerbar(self):
        self.options_menu()

        hb = Gtk.HeaderBar()
        hb.set_show_close_button(True)
        hb.props.title = "pyAstroRef"
        self.set_titlebar(hb)

        hb.pack_end(self.button_opt)

        hb.pack_start(self.search)


    def on_click_load_options(self, button):
        options.OptionsMenu()

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

        journal.ShowJournal(target,self.right_panel,query)

    def setup_panels(self):
        self.panels = Gtk.HPaned()

        self.right_panel = Gtk.Notebook(scrollable=True)
        self.right_panel.set_vexpand(True)
        self.right_panel.set_hexpand(True)

        self.left_panel = leftpanel.LeftPanel(self.right_panel)
        def func():
            return []
        journal.ShowJournal(func,self.right_panel, 'Home')
        
        self.right_panel.show_all()

        self.panels.pack1(self.left_panel.treeview,False,False)
        self.panels.pack2(self.right_panel,True,True)


    def setup_grid(self):
        self.grid = Gtk.Grid()
        self.grid.set_orientation(Gtk.Orientation.VERTICAL)

        self.add(self.grid)

        self.grid.add(self.panels)
