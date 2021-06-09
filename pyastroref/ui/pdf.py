# SPDX-License-Identifier: GPL-2.0-or-later

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

from . import utils
from . import journal
from . import libraries

from ..pdf import pdfWindow

EvinceDocument.init()


class ShowPDF(Gtk.VBox):
    def __init__(self, data, notebook):
        Gtk.VBox.__init__(self)

        self.has_search_open = False

        self.data = data
        self.notebook = notebook


        self.astroref_name = self.data.bibcode

        self.header = PDFPopupWindow(self.notebook, self, self.data)

        self._filename = self.data.filename(True)

        self.add_page()

        utils.thread(self.download_and_show)

        if not os.path.exists(self._filename):
            utils.file_error_window(self.data.bibcode)
            return 


    def download_and_show(self):
        GLib.idle_add(self.header.spin_on)
        try:
            self.data.pdf(self._filename)
        except Exception:
            pass

        if not os.path.exists(self._filename):
            GLib.idle_add(self.header.spin_off)
            return 

        self.pdf = pdfWindow.pdfWin(self._filename)

        GLib.idle_add(self.add,self.pdf)
        GLib.idle_add(self.header.spin_off)
        self.header.pdf = self.pdf
        return

    def add_page(self):
        for p in range(self.notebook.get_n_pages()):
            page = self.notebook.get_nth_page(p)
            if self.data.bibcode == page.astroref_name:
                self.notebook.set_current_page(p)
                self.notebook.show_all()
                return

        self.page_num = self.notebook.append_page(self, self.header)
        self.notebook.set_tab_reorderable(self, True)
        self.notebook.show_all()

    def searchbar(self, widget, event=None):
        self.pdf.searchbar(widget,event)


class PDFPopupWindow(Gtk.EventBox):
    def __init__(self, notebook, page, data):
        Gtk.EventBox.__init__(self)

        self.notebook = notebook
        self.page = page
        self.data = data
        self.pdf = None

        self.spinner = Gtk.Spinner()
        self.header = Gtk.HBox()
        self.title_label = Gtk.Label(label=self.data.name)
        image = Gtk.Image()
        image.set_from_icon_name('window-close', Gtk.IconSize.MENU)

        self.title_label.set_has_tooltip(True)
        self.title_label.connect('query-tooltip' , self.tooltip)

        self.close_button = Gtk.Button()
        self.close_button.set_image(image)
        self.close_button.set_relief(Gtk.ReliefStyle.NONE)
        self.close_button.connect('clicked', self.on_tab_close)

        GLib.idle_add(self.spin_on)
        self.header.pack_start(self.title_label,
                          expand=True, fill=True, padding=0)
        self.header.pack_end(self.spinner,
                        expand=False, fill=False, padding=0)

        self.header.show_all()

        self.button = {}

        self.popover = Gtk.Popover()

        vbox = Gtk.VBox(orientation=Gtk.Orientation.VERTICAL)

        self.button['open_ads'] = Gtk.LinkButton(uri=self.data.ads_url,label='Open ADS')
        vbox.pack_start(self.button['open_ads'], False, True, 0)

        if len(self.data.arxiv_url):
            self.button['open_arxiv'] = Gtk.LinkButton(uri=self.data.arxiv_url,label='Open Arxiv')
            vbox.pack_start(self.button['open_arxiv'], False, True, 0)

        if len(self.data.journal_url):
            self.button['open_journal'] = Gtk.LinkButton(uri=self.data.journal_url,label='Open '+self.data.journal)
            vbox.pack_start(self.button['open_journal'], False, True, 0)
        vbox.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, True, 10)

        self.button['copy_bibtex'] = Gtk.Button.new_with_label("Copy Bibtex")
        vbox.pack_start(self.button['copy_bibtex'], False, True, 0)

        self.button['cites'] = Gtk.Button.new_with_label("Citations")
        vbox.pack_start(self.button['cites'], False, True, 0)

        self.button['refs'] = Gtk.Button.new_with_label("References")
        vbox.pack_start(self.button['refs'], False, True, 0)

        vbox.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, True, 10)

        self.button['add_lib'] = Gtk.Button.new_with_label("Add to library")
        vbox.pack_start(self.button['add_lib'], False, True, 0)


        vbox.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, True, 10)


        self.button['save'] = Gtk.Button.new_with_label("Save")
        vbox.pack_start(self.button['save'], False, True, 0)

        self.button['save_as'] = Gtk.Button.new_with_label("Save as")
        vbox.pack_start(self.button['save_as'], False, True, 0)

        self.button['print'] = Gtk.Button.new_with_label("Print")
        vbox.pack_start(self.button['print'], False, True, 0)

        vbox.pack_start(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL), False, True, 10)

        self.button['close'] = Gtk.Button.new_with_label("Close")
        vbox.pack_start(self.button['close'], False, True, 0)

        self.button['del'] = Gtk.Button.new_with_label("Delete")
        vbox.pack_start(self.button['del'], False, True, 0)

        vbox.show_all()

        self.popover.add(vbox)
        self.popover.set_position(Gtk.PositionType.BOTTOM)
        
        self.popover.set_relative_to(self.header)

        self.add(self.header)

        self.connect("button-press-event", self.button_press)

        self.button['copy_bibtex'].connect("button-press-event", self.bp_bib)
        self.button['cites'].connect("button-press-event", self.bp_cites)
        self.button['refs'].connect("button-press-event", self.bp_refs)
        self.button['add_lib'].connect("button-press-event", self.bp_add_lib)

        self.button['save'].connect("button-press-event", self.bp_save)
        self.button['save_as'].connect("button-press-event", self.bp_save_as)
        self.button['print'].connect("button-press-event", self.bp_print)

        self.button['close'].connect("button-press-event", self.bp_close)
        self.button['del'].connect("button-press-event", self.bp_del)

    def tooltip(self, widget, x, y, keyboard, tooltip):
        tooltip.set_text(self.data.title)
        return True


    def on_tab_close(self, button):
        self.notebook.remove_page(self.notebook.page_num(self.page))

    def button_press(self, widget, event):
        if event.button == Gdk.BUTTON_PRIMARY:
            self.notebook.set_current_page(self.notebook.page_num(self.page))
            return True
        elif event.button == Gdk.BUTTON_SECONDARY:
            #make widget popup
            self.popover.popup()
            return True
        return False

    def spin_on(self):
        self.spinner.start()

    def spin_off(self):
        self.spinner.stop()
        self.header.remove(self.spinner)
        self.header.pack_end(self.close_button,
                        expand=False, fill=False, padding=0)
        self.header.show_all()


    def bp_bib(self, widget, event):
        utils.clipboard(self.data.bibtex())
        return True

    def bp_cites(self, widget, event):
        journal.ShowJournal(self.data.citations,self.notebook,'Cites:'+self.data.name)
        return True

    def bp_refs(self, widget, event):
        journal.ShowJournal(self.data.references,self.notebook,'Refs:'+self.data.name)
        return True

    def bp_add_lib(self, widget, event):
        libraries.Add2Lib([self.data.bibcode])

    def bp_close(self, widget, event):
        self.on_tab_close(widget)

    def bp_del(self, widget, event):
        os.remove(self.data.filename(True))
        self.on_tab_close(widget)

    def bp_print(self, widget, event):
        self.pdf.pdf.print()

    def bp_save(self, widget, event):
        self.pdf.pdf.save()

    def bp_save_as(self, widget, event):
        self.pdf.pdf.save_as()