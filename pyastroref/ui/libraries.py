# SPDX-License-Identifier: GPL-2.0-or-later

import os
import sys
import threading

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk, GObject, Gdk

import pyastroapi.libraries as lib

_alllibs = None

def _init_libs():
    global _alllibs
    if _alllibs is not None:
        _alllibs = lib.libraries()
        GLib.idle_add(_alllibs.update)


def get(name):
    _init_libs()

    if _alllibs is not None:
        return _alllibs[name]

def list_all():
    _init_libs()

    if _alllibs is not None:
        return _alllibs.keys()



class Add2Lib(Gtk.Window):
    def __init__(self, bibcodes=[]):
        Gtk.Window.__init__(self, title="Add to library")

        self.bibcodes = bibcodes

        self.set_border_width(10)
        self.set_position(Gtk.WindowPosition.CENTER)


        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)


        self.combo = Gtk.ComboBoxText()

        _init_libs()

        for i in _alllibs.names():
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
            def target():
                _alllibs[lib].add(self.bibcodes)

            thread = threading.Thread(target=target)
            thread.daemon = True
            thread.start()  

        self.destroy()

class EditLibrary(Gtk.Window):
    def __init__(self, name=None,add=True, callback=None):
        self._add = add
        if self._add:
            title = 'New library'
        else:
            title = 'Edit library'

        Gtk.Window.__init__(self, title=title)

        self._name = name
        self._description = ''
        self._public=False
        self._callback = callback

        _init_libs()

        if self._name is not None:
            if self._name in _alllibs:
                self._lib = _alllibs[self._name]
                self._description = self._lib.description
                self._public = self._lib.public


        self.set_border_width(10)
        self.set_position(Gtk.WindowPosition.CENTER)


        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.add(vbox)

        listbox = Gtk.ListBox()
        listbox.set_selection_mode(Gtk.SelectionMode.NONE)
        vbox.pack_start(listbox, True, True, 0)

        row = Gtk.ListBoxRow()
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=50)
        row.add(hbox)

        label = Gtk.Label(label="Name")
        self.name = Gtk.Entry()
        if self._name is not None:
            self.name.set_text(self._name)
        hbox.pack_start(label, True, True, 0)
        hbox.pack_start(self.name, True, True, 0)
        listbox.add(row)

        row = Gtk.ListBoxRow()
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=50)
        row.add(hbox)
        label = Gtk.Label(label="Description")

        self.description = Gtk.Entry()
        self.description.set_text(self._description)
        hbox.pack_start(label, True, True, 0)
        hbox.pack_start(self.description, True, True, 0)
        listbox.add(row)

        row = Gtk.ListBoxRow()
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=50)
        row.add(hbox)
        label = Gtk.Label(label="Visibility")

        self.button1 = Gtk.RadioButton.new_with_label_from_widget(None, "Public")
        self.button2 = Gtk.RadioButton.new_from_widget(self.button1)
        self.button2.set_label("Private")

        #button1.connect("toggled", self.on_button_toggled, "public")
        #button2.connect("toggled", self.on_button_toggled, "private")
        hbox.pack_start(label, False, False, 0)
        hbox.pack_start(self.button1, False, False, 0)
        hbox.pack_start(self.button2, False, False, 0)

        if self._public:
            self.button1.set_active(True)
        else:
            self.button2.set_active(True)
        
        listbox.add(row)

        row = Gtk.ListBoxRow()
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=50)
        row.add(hbox)

        save = Gtk.Button(label='Save')
        save.connect('clicked', self.on_save)

        hbox.pack_start(save, True,True,0)
        listbox.add(row)

        self.show_all()

    def on_save(self, button):
        name = self.name.get_text()
        description = self.description.get_text()

        _init_libs()

        if self._add:
            def target():
                _alllibs.new(name,description,self.button1.get_active())
        else:
            def target():
                _alllibs.edit(self._name, name,description,self.button1.get_active())

        thread = threading.Thread(target=target)
        thread.daemon = True
        thread.start()     


        if self._callback is not None:
            self._callback(name)
        self.destroy()
