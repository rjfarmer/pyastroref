# SPDX-License-Identifier: GPL-2.0-or-later

import os
import sys
import threading

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk, GObject, Gdk

import pyastroapi.api.token as token

from . import utils


class OptionsMenu(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="Options")
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_keep_above(True)
    
        self.setup_adsabs()
        self.setup_orcid()
        self.setup_folder()

        self.setup_save()
        self.setup_dm()

        self.setup_grid()

        self.show_all()   

    def setup_adsabs(self):
        self.ads_entry = Gtk.Entry()
        self.ads_entry.set_width_chars(50)

        t = token.get_token()
        if t is not None:
            self.ads_entry.set_text(token.get_token())
        self.ads_entry.set_visibility(False)
        self.ads_entry.set_icon_from_icon_name(Gtk.EntryIconPosition.SECONDARY,'dialog-password-symbolic')
        self.ads_entry.connect('icon-press',self.flip_visible)

        self.ads_label = Gtk.LinkButton(uri='https://ui.adsabs.harvard.edu/user/settings/token',label='ADSABS ID')


    def setup_orcid(self):
        self.orcid_entry = Gtk.Entry()
        t = token.get_orcid()
        if t is not None:
            self.orcid_entry.set_text(token.get_orcid())
        self.orcid_entry.set_width_chars(50)

        self.orcid_label = Gtk.LinkButton(uri='https://orcid.org',label='ORCID')


    def setup_grid(self):
        self.grid = Gtk.Grid()
        self.add(self.grid)
        self.grid.add(self.ads_label)
        self.grid.attach_next_to(self.ads_entry,self.ads_label,
                            Gtk.PositionType.RIGHT,1,1)
     
        self.grid.attach_next_to(self.orcid_label,self.ads_label,
                            Gtk.PositionType.BOTTOM,1,1)
        self.grid.attach_next_to(self.orcid_entry,self.orcid_label,
                            Gtk.PositionType.RIGHT,1,1)

        self.grid.attach_next_to(self.file_label,self.orcid_label,
                            Gtk.PositionType.BOTTOM,1,1)
        self.grid.attach_next_to(self.folder_entry,self.file_label,
                            Gtk.PositionType.RIGHT,1,1)   

        self.grid.attach_next_to(self.dm_label,self.file_label,
                            Gtk.PositionType.BOTTOM,1,1)
        self.grid.attach_next_to(self.dm_button,self.dm_label,
                            Gtk.PositionType.RIGHT,1,1)   


        self.grid.attach_next_to(self.save_button,self.dm_label,
                            Gtk.PositionType.BOTTOM,2,1)  

    def setup_dm(self):
        self.dm_label = Gtk.Label(label='Dark mode')
        self.dm_button = Gtk.Switch()
        self.dm_button.connect("notify::active", self.on_switch_activated)
        self.dm_button.set_active(utils.get_dm())
        self.dm_button.set_halign(Gtk.Align.CENTER)

    def setup_save(self):
        self.save_button = Gtk.Button(label="Save")
        self.save_button.connect("clicked", self.save)

    def setup_folder(self):
        self.pdffolder = utils.settings.pdffolder
        label = "Choose Folder"
        if self.pdffolder is not None:
            label = self.pdffolder

        self.folder_entry = Gtk.Button(label=label)
        self.folder_entry.connect("clicked", self.on_file_clicked)

        self.file_label = Gtk.Label(label='Save folder')


    def save_ads(self, button):
        utils.settings.adsabs = self.ads_entry.get_text()

    def save_orcid(self, button):
        utils.settings.orcid = self.orcid_entry.get_text()

    def flip_visible(self, *args):
        if self.ads_entry.get_visibility():
            self.ads_entry.set_visibility(False)
        else:
            self.ads_entry.set_visibility(True)

    def on_file_clicked(self, widget):
        dialog = Gtk.FileChooserDialog(
            title="Please choose a folder",
            transient_for=self,
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
        utils.settings.adsabs = self.ads_entry.get_text()
        utils.settings.orcid = self.orcid_entry.get_text()
        utils.settings.pdffolder = self.pdffolder
        utils.set_dm(self.dm_button.get_active())
        self.destroy()

    def on_switch_activated(self, switch, gparam):
        pass