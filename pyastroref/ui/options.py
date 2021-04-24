# SPDX-License-Identifier: GPL-2.0-or-later

import os
import sys
import threading

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk, GObject, Gdk

from ..papers import adsabs as ads

adsData = ads.adsabs()

class OptionsMenu(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="Options")
        self.set_position(Gtk.WindowPosition.CENTER)
        self.pdffolder = adsData.pdffolder
        grid = Gtk.Grid()
        self.add(grid)

        self.ads_entry = Gtk.Entry()
        self.ads_entry.set_width_chars(50)

        if adsData.token is not None:
            self.ads_entry.set_text(adsData.token)

        self.orcid_entry = Gtk.Entry()
        if adsData.orcid is not None:
            self.orcid_entry.set_text(adsData.orcid)
        self.orcid_entry.set_width_chars(50)

        label = "Choose Folder"
        if adsData.pdffolder is not None:
            label = adsData.pdffolder
            print(adsData.pdffolder)

        self.folder_entry = Gtk.Button(label=label)
        self.folder_entry.connect("clicked", self.on_file_clicked)

        ads_label = Gtk.LinkButton(uri='https://ui.adsabs.harvard.edu/user/settings/token',label='ADSABS ID')
        orcid_label = Gtk.LinkButton(uri='https://orcid.org',label='ORCID')

        file_label = Gtk.Label(label='Save folder')

        save_button = Gtk.Button(label="Save")
        save_button.connect("clicked", self.save)


        grid.add(ads_label)
        grid.attach_next_to(self.ads_entry,ads_label,
                            Gtk.PositionType.RIGHT,1,1)
     
        grid.attach_next_to(orcid_label,ads_label,
                            Gtk.PositionType.BOTTOM,1,1)
        grid.attach_next_to(self.orcid_entry,orcid_label,
                            Gtk.PositionType.RIGHT,1,1)

        grid.attach_next_to(file_label,orcid_label,
                            Gtk.PositionType.BOTTOM,1,1)
        grid.attach_next_to(self.folder_entry,file_label,
                            Gtk.PositionType.RIGHT,1,1)   

        grid.attach_next_to(save_button,file_label,
                            Gtk.PositionType.BOTTOM,2,1)  

        self.show_all()   

    def save_ads(self, button):
        adsData.token = self.ads_entry.get_text()

    def save_orcid(self, button):
        adsData.orcid = self.orcid_entry.get_text()

    def on_file_clicked(self, widget):
        dialog = Gtk.FileChooserDialog(
            title="Please choose a folder",
            action=Gtk.FileChooserAction.SELECT_FOLDER
            )

        dialog.add_buttons(
            Gtk.STOCK_CANCEL,
            Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN,
            Gtk.ResponseType.OK,
        )

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            f = dialog.get_filename()
            widget.set_label(f)
            self.pdffolder = f
            
        dialog.destroy()

    def save(self, widegt):
        adsData.token = self.ads_entry.get_text()
        adsData.orcid = self.orcid_entry.get_text()
        adsData.pdffolder = self.pdffolder
        self.destroy()