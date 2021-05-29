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

from ..ui import utils

class pdfWin(Gtk.VBox):
    def __init__(self, filename):
        Gtk.VBox.__init__(self)
        self.has_search_open = False

        self._filename = filename

        self.pdf = EvinceDocument.Document.factory_get_document('file://'+self._filename)

        self.view = EvinceView.View()
        self.model = EvinceView.DocumentModel()
        self.model.set_document(self.pdf)
        self.view.set_model(self.model)
        self.view.find_set_highlight_search(True)

        self.header = pdfHead(self)
        self.pack_start(self.header,False,False,0)

        self.sb = Gtk.ScrolledWindow()
        self.sb.add(self.view)

        self.view.connect('key-press-event', self.key_press)

        self.pack_start(self.sb,True,True,0)

        self.show_all()


    def searchbar(self, widget, event=None):
        pass

    def key_press(self, widget, event=None):
        keyval = event.keyval
        keyval_name = Gdk.keyval_name(keyval)
        state = event.state
        ctrl = (state & Gdk.ModifierType.CONTROL_MASK)

        if ctrl:
            if keyval_name == 'c':
                utils.clipboard(self.view.get_selected_text())
                return
            elif keyval_name == 'h':
                #highlight
                return
            elif keyval_name == 'a':
                #Annotate
                return
            elif keyval_name == 's':
                #save
                return
            elif keyval_name == 'p':
                #print
                return

        if keyval_name == 'Page_Up':
            cur_page = self.model.get_page()
            self.model.set_page(cur_page-1)
            return

        if keyval_name == 'Page_Down':
            cur_page = self.model.get_page()
            self.model.set_page(cur_page+1)
            return

        if keyval_name == 'Home':
            self.model.set_page(0)
            return

        if keyval_name == 'End':
            self.model.set_page(self.pdf.get_n_pages())
            return


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

        self.sb.connect("changed", self.search)


    def add_button(self,button):
        self.bs.append(Gtk.Button())
        image = Gtk.Image()
        image.set_from_icon_name(button[0], Gtk.IconSize.BUTTON)
        self.bs[-1].set_image(image)
        self.bs[-1].connect('clicked',button[1])
        button[2].pack_start(self.bs[-1],False,False,0)


    def on_next(self, button):
        self.parent.view.find_next()

    def on_prev(self, button):
        self.parent.view.find_previous()


    def search(self, widget):
        query = widget.get_text().lower()
        print(query)

        search = EvinceView.JobFind()
        self.parent.view.find_started(search)


class pdfHead(Gtk.HBox):
    def __init__(self, parent):
        Gtk.HBox.__init__(self)
        self.parent = parent

        buttons = [
            {'image':'document-save','callback':None,'tooltip':'Save PDF','button':None},
            {'image':'document-print','callback':None,'tooltip':'Print PDF','button':None},
            {'image':'view-fullscreen','callback':None,'tooltip':'Fullscreen','button':None},
            {'image':'zoom-in','callback':self.zoom_in,'tooltip':'Zoom in','button':None},
            {'image':'zoom-out','callback':self.zoom_out,'tooltip':'Zoom out','button':None},
            {'image':'object-rotate-left','callback':self.rotate_left,'tooltip':'Rotate left','button':None},
            {'image':'object-rotate-right','callback':self.rotate_right,'tooltip':'Rotate right','button':None},
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


    def zoom_in(self,button):
        self.parent.model.set_scale(self.parent.model.get_scale()*1.1)

    def zoom_out(self,button):
        self.parent.model.set_scale(self.parent.model.get_scale()*0.9)

    def rotate_left(self, button):
        rotation = self.parent.model.get_rotation()

        rotation -= 90
        if rotation < 0:
            rotation =  0

        self.parent.model.set_rotation(rotation)

    def rotate_right(self, button):
        rotation = self.parent.model.get_rotation()

        rotation += 90
        if rotation > 360:
            rotation =  0

        self.parent.model.set_rotation(rotation)