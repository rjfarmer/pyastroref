# SPDX-License-Identifier: GPL-2.0-or-later

import os
import sys
import threading
import glob
import datetime
from pathlib import Path

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk, GObject, Gdk

import pyastroapi.search as search
import pyastroapi.articles as articles

from . import options, journal, leftpanel, utils, pdf



class MainWindow(Gtk.Window):
    def __init__(self):
        self._init = False
        self.settings = {}
        self.pages = {}

        Gtk.Window.__init__(self, title="pyAstroRef")

        utils.set_dm()

        self.connect("destroy", Gtk.main_quit)
        self.set_hide_titlebar_when_maximized(False)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.maximize()

        self.setup_panels()
        self.setup_search_bar()
        self.setup_headerbar()

        self.setup_grid()  

        if utils.settings.adsabs is None:
            options.OptionsMenu()

        self.show_all()

        _cleanup_caches()
        GLib.timeout_add_seconds(24*60*60, _cleanup_caches)


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
        self.search = AdsSearchEntry(self.right_panel)
        self.set_default(self.search)


    def setup_panels(self):
        self.panels = Gtk.HPaned()

        self.rp_box = Gtk.VBox()

        self.right_panel = Gtk.Notebook(scrollable=True)

        self.right_panel.set_vexpand(True)
        self.right_panel.set_hexpand(True)

        self.rp_box.pack_start(self.right_panel,True,True,0)

        self.left_panel = leftpanel.LeftPanel(self.right_panel)
        def func():
            return []
        journal.JournalPage(func,self.right_panel, 'Home')
        
        self.right_panel.show_all()

        self.panels.pack1(self.left_panel.treeview,False,False)
        self.panels.pack2(self.rp_box,True,True)

        self.rp_box.pack_start(utils._statusbar,False,False,0)


    def setup_grid(self):
        self.grid = Gtk.Grid()
        self.grid.set_orientation(Gtk.Orientation.VERTICAL)

        self.add(self.grid)

        self.grid.add(self.panels)


class AdsSearchEntry(Gtk.SearchEntry):
    def __init__(self, rp):
        Gtk.SearchEntry.__init__(self)
        self.set_placeholder_text('Search ADS ...')
        self.connect("activate",self.on_click_search)

        self.set_can_default(True)
        self.set_hexpand(True)

        self.rp = rp
        self.show_all()

    def on_click_search(self, button):
        query = self.get_text()

        if len(query) == 0:
            return

        p = self.rp.get_nth_page(self.rp.get_current_page())
        if isinstance(p, pdf.ShowPDF):
            query = query + " references({p.data.bibcode})"

        def target():
            return articles.journal(search = query)

        journal.JournalPage(target,self.rp,query)


def _cleanup_caches():
    folder = utils.settings.cache

    yesterday = datetime.date.today() - datetime.timedelta(days=1)
    for file in glob.glob(os.path.join(folder,'*')):
        path = Path(file)
        last_modified = datetime.date.fromtimestamp(path.stat().st_mtime)
        if last_modified < yesterday:
            os.remove(file)