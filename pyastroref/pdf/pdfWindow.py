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

        self.header = pdfHead(self)
        self.pack_start(self.header,False,False,0)

        self.sb = Gtk.ScrolledWindow()
        self.sb.add(self.pdf_view)

        self.pack_start(self.sb,True,True,0)

        self.show_all()

    def searchbar(self, widget, event=None):
        pass


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

        self.bs = []

        for i in buttons1:
            self.add_button(i)

        self.pack_start(hb,True,True,0)


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


class pdfHead(Gtk.HBox):
    def __init__(self, parent):
        Gtk.HBox.__init__(self)
        self.parent = parent

        buttons = [
            {'image':'document-save','callback':None,'tooltip':'Save PDF','button':None},
            {'image':'document-print','callback':None,'tooltip':'Print PDF','button':None},
            {'image':'view-fullscreen','callback':None,'tooltip':'Fullscreen','button':None},
            {'image':'zoom-in','callback':None,'tooltip':'Zoom in','button':None},
            {'image':'zoom-out','callback':None,'tooltip':'Zoom out','button':None},
            {'image':'object-rotate-left','callback':None,'tooltip':'Rotate left','button':None},
            {'image':'object-rotate-right','callback':None,'tooltip':'Rotate right','button':None},
            {'image':'applications-graphics','callback':None,'tooltip':'Highlight text','button':None},
            {'image':'font-x-generic','callback':None,'tooltip':'Add annotation','button':None}
        ]
        
        for i in buttons:
            self.add_button(i)

        sb = SearchBar(self.parent)
        self.pack_end(sb,True,True,0)

        self.show_all()


    def add_button(self,button):
        button['button'] = Gtk.Button()
        image = Gtk.Image()

        image.set_from_icon_name(button['image'], Gtk.IconSize.BUTTON)
        button['button'].set_image(image)

        if button['callback'] is not None:
            button['button'].connect('clicked',button['callback'])
        self.pack_start(button['button'],False,False,0)
        button['button'].set_tooltip_text(button['tooltip'])