import os
import sys
import threading
import tempfile
import shutil

import gi
gi.require_version("Gtk", "3.0")
gi.require_version('EvinceDocument', '3.0')
gi.require_version('EvinceView', '3.0')
from gi.repository import GLib, Gtk, GObject, GdkPixbuf, Gdk, Gio
from gi.repository import EvinceDocument
from gi.repository import EvinceView

EvinceDocument.init()

from ..ui import utils

class pdfWin(Gtk.VBox):
    def __init__(self, filename):
        Gtk.VBox.__init__(self)
        self.has_search_open = False

        self._filename = filename

        self.pdf = _Pdf(self._filename)

        self.header = pdfHead(self.pdf)
        self.pack_start(self.header,False,False,0)

        self.sb = Gtk.ScrolledWindow()
        self.sb.add(self.pdf.view)

        self.pack_start(self.sb,True,True,0)

        self.show_all()

class _Pdf(object):
    def __init__(self, filename):
        self._filename = filename

        self.load_pdf()

        # Autosave pdf every 1 minutes (set in milliseconds)
        #GLib.timeout_add(1 * 60000 ,self.save)
        # Autosave pdf every 5 minutes (set in milliseconds)
        GLib.timeout_add(5 * 60000 ,self.save)

    @property
    def _uri(self):
        return 'file://'+self._filename

    def load_pdf(self):
        self.pdf = EvinceDocument.Document.factory_get_document(self._uri)

        self.view = EvinceView.View()
        self.model = EvinceView.DocumentModel()
        self.model.set_document(self.pdf)
        self.view.set_model(self.model)
        self.view.find_set_highlight_search(True)

        self.view.connect('key-press-event', self.key_press)


    def start_page(self, *args):
        self.model.set_page(0)

    def end_page(self, *args):
        self.model.set_page(self.pdf.get_n_pages())

    def next_page(self, *args):
        cur_page = self.model.get_page()
        self.model.set_page(cur_page+1)

    def prev_page(self, *args):
        cur_page = self.model.get_page()
        self.model.set_page(cur_page-1)

    def highlighted_text(self, *args):
        return self.view.get_selected_text()

    def rotate_left(self, *args):
        rotation = self.model.get_rotation()

        rotation -= 90

        self.model.set_rotation(rotation)

    def rotate_right(self, *args):
        rotation = self.model.get_rotation()

        rotation += 90

        self.model.set_rotation(rotation)

    def save(self):
        tmp_file = tempfile.NamedTemporaryFile(suffix='.pdf',delete=False)
        filename = tmp_file.name
        if self.pdf.save('file://'+filename):
            shutil.move(filename, self._filename)
        tmp_file.close()
        self.model.get_document().load(self._uri)
        self.view.reload()

    def key_press(self, widget, event=None):
        keyval = event.keyval
        keyval_name = Gdk.keyval_name(keyval)
        state = event.state
        ctrl = (state & Gdk.ModifierType.CONTROL_MASK)

        print(keyval_name)
        if ctrl:
            if keyval_name == 'c':
                self.copy_text()
                return
            elif keyval_name == 'h':
                self.highlight_text()
                return
            elif keyval_name == 'a':
                #Annotate
                return
            elif keyval_name == 's':
                self.save()
                return
            elif keyval_name == 'p':
                self.print()
                return
            elif keyval_name == 'Left':
                self.rotate_left()
                return
            elif keyval_name == 'Right':
                self.rotate_right()
                return

        if keyval_name == 'Page_Up':
            self.prev_page()
            return

        if keyval_name == 'Page_Down':
            self.next_page()
            return

        if keyval_name == 'Home':
            self.start_page()
            return

        if keyval_name == 'End':
            self.end_page()
            return


    def copy_text(self):
        text = self.highlighted_text().replace('\n',' ')
        utils.clipboard(text)
    def print(self):
        print_op = Gtk.PrintOperation()
        print_op.connect("begin-print", self.begin_print)
        print_op.connect("draw-page", self.draw_page)
        result = print_op.run(Gtk.PrintOperationAction.PRINT_DIALOG)

        if result == Gtk.PrintOperationResult.ERROR:
            message = self.operation.get_error()

            dialog = Gtk.MessageDialog(None,
                                       0,
                                       Gtk.MessageType.ERROR,
                                       Gtk.ButtonsType.CLOSE,
                                       message)

            dialog.run()
            dialog.destroy()

    def begin_print(self,operation,*args):
        operation.set_n_pages(self.pdf.get_n_pages())

    def draw_page(self,operation, context, page_nr, *args):
        cairo = context.get_cairo_context()
        self.pdf.print_page(self.pdf.get_page(page_nr),cairo)


    def highlight_text(self):
        self.view.add_text_markup_annotation_for_selected_text()


    def save_as(self):
        utils.save_as(self._filename, self.save_with_filename)

    def save_with_filename(self, filename):
        self._filename = filename
        self.save()


class SearchBar(Gtk.HBox):
    def __init__(self, pdf):
        Gtk.HBox.__init__(self)

        self.pdf = pdf

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
        self.pdf.view.find_next()

    def on_prev(self, button):
        self.pdf.view.find_previous()


    def search(self, widget):
        query = widget.get_text().lower()
        print(query)

        search = EvinceView.JobFind()
        self.pdf.view.find_started(search)


class pdfHead(Gtk.HBox):
    def __init__(self, pdf):
        Gtk.HBox.__init__(self)
        self.pdf = pdf

        buttons = [
            {'image':'applications-graphics','callback':None,'tooltip':'Highlight text','button':None},
            {'image':'font-x-generic','callback':None,'tooltip':'Add annotation','button':None}
        ]
        
        for i in buttons:
            self.add_button(i)


        sb = SearchBar(self.pdf)
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
