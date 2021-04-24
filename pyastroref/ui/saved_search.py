# SPDX-License-Identifier: GPL-2.0-or-later

import os
import sys
import threading

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk, GObject, Gdk



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