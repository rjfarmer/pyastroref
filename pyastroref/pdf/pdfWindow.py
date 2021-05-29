import os
import sys
import threading

import gi
gi.require_version("Gtk", "3.0")
gi.require_version('EvinceDocument', '3.0')
gi.require_version('EvinceView', '3.0')
from gi.repository import GLib, Gtk, GObject, GdkPixbuf, Gdk
from gi.repository import EvinceDocument
from gi.repository import EvinceView

EvinceDocument.init()


class pdfWin(Gtk.VBox):
    def __init__(self, filename):
        Gtk.VBox.__init__(self)
        self.has_search_open = False

        self._filename = filename

        self.pdf = EvinceDocument.Document.factory_get_document('file://'+self._filename)

        self.pdf_view = EvinceView.View()
        self.pdf_model = EvinceView.DocumentModel()
        self.pdf_model.set_document(self.pdf)
        self.pdf_view.set_model(self.pdf_model)

        self.sb = Gtk.ScrolledWindow()
        self.sb.add(self.pdf_view)

        self.add(self.sb)

        self.show_all()

    def searchbar(self, widget, event=None):
        if event is None:
            return False

        keyval = event.keyval
        keyval_name = Gdk.keyval_name(keyval)
        state = event.state
        ctrl = (state & Gdk.ModifierType.CONTROL_MASK)

        if ctrl and keyval_name == 'f':
            if not self.has_search_open:
                sb = SearchBar(self)     
                self.pack_start(sb,False,False,0)
                self.reorder_child(sb,0)
                sb.show_all()
                self.has_search_open = True
                return True

        return False


class SearchBar(Gtk.HBox):
    def __init__(self, parent):
        Gtk.HBox.__init__(self)

        self.parent = parent

        hb = Gtk.HBox()

        self.sb = Gtk.SearchEntry()
        hb.pack_start(self.sb,True,True,0)

        buttons1 = [
            ['go-up',self.on_next,hb],
            ['go-down',self.on_prev,hb],
        ]

        buttons2 = [
            ['window-close-symbolic',self.on_close,self]
        ]

        self.bs = []

        for i in buttons1:
            self.add_button(i)


        self.pack_start(hb,True,True,0)

        for i in buttons2:
            self.add_button(i)

    def add_button(self,button):
        self.bs.append(Gtk.Button())
        image = Gtk.Image()
        image.set_from_icon_name(button[0], Gtk.IconSize.BUTTON)
        self.bs[-1].set_image(image)
        self.bs[-1].connect('clicked',button[1])
        button[2].pack_start(self.bs[-1],False,False,0)


    def on_next(self, button):
        pass

    def on_prev(self, button):
        pass

    def on_close(self, button):
        self.parent.remove(self)
        self.parent.has_search_open = False