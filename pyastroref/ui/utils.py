# SPDX-License-Identifier: GPL-2.0-or-later

import os
import sys
import random
import string
import threading

from pathlib import Path
from appdirs import AppDirs

dirs = AppDirs("pyAstroRef")

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk, GObject, Gdk, Gio

import pyastroapi.api.token as token

_search_fields = "abstract,author,bibcode,pubdate,title,pub,year,citation_count,reference"


class Settings:
    def __init__(self):
        # Where to store PDF's
        self._PDFFOLDER_FILE = os.path.join(dirs.user_config_dir,'pdfs')
        # Where to store list of journals
        self._ALL_JOURNALS_LIST = os.path.join(dirs.user_config_dir,'all_journals')
        # Where to store list of to display
        self._JOURNALS_LIST = os.path.join(dirs.user_config_dir,'journals')
        # Dark mode?
        self._DARK_MODE_FILE = os.path.join(dirs.user_config_dir,'dark_mode')
        # Cache location
        self.cache = dirs.user_cache_dir
        # Bibtext cace
        self.bibtex_cache = os.path.join(dirs.user_cache_dir,'bibtex')

        os.makedirs(self.cache,exist_ok=True)
        os.makedirs(self.bibtex_cache,exist_ok=True)


    def _save_key_file(self,filename,key):
        os.makedirs(os.path.dirname(filename),exist_ok=True)
        with open(filename,'w') as f:
            print(key,file=f)

    def _read_key_file(self, filename):
        os.makedirs(os.path.dirname(filename),exist_ok=True) # Handle making folders on first run
        try:
            with open(filename,'r') as f:
                result = f.readline().strip() 
        except FileNotFoundError:
            return None
        return result

    @property
    def pdffolder(self):
        return self._read_key_file(self._PDFFOLDER_FILE)

    @pdffolder.setter
    def pdffolder(self, value):
        return self._save_key_file(self._PDFFOLDER_FILE, value)

    @property
    def all_journals(self):
        return self._read_key_file(self._ALL_JOURNALS_LIST)

    @all_journals.setter
    def all_journals(self, value):
        return self._save_key_file(self._ALL_JOURNALS_LIST, value)

    @property
    def journals(self):
        return self._read_key_file(self._JOURNALS_LIST)

    @journals.setter
    def journals(self, value):
        return self._save_key_file(self._JOURNALS_LIST, value)

    @property
    def dark_mode(self):
        return self._read_key_file(self._DARK_MODE_FILE)

    @dark_mode.setter
    def dark_mode(self, value):
        return self._save_key_file(self._DARK_MODE_FILE, value)

    @property
    def adsabs(self):
        return token.get_token()

    @adsabs.setter
    def adsabs(self, value):
        return token.save_token(value)

    @property
    def orcid(self):
        return token.get_orcid()

    @orcid.setter
    def orcid(self, value):
        return token.save_orcid(value)


settings = Settings()

_statusbar = Gtk.Statusbar()

def clipboard(data):
    clip = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
    clip.set_text(data,-1)


def ads_error_window():
    dialog = Gtk.MessageDialog(
        flags=0,
        message_type=Gtk.MessageType.INFO,
        buttons=Gtk.ButtonsType.OK,
        text="ADSABS error",
    )
    dialog.format_secondary_text(
        "Either adsabs is down or your ads token is bad"
    )
    dialog.run()

    dialog.destroy()


def orcid_error_window():
    dialog = Gtk.MessageDialog(
        flags=0,
        message_type=Gtk.MessageType.INFO,
        buttons=Gtk.ButtonsType.OK,
        text="ORCID not set",
    )
    dialog.format_secondary_text(
        "Please set up your orcid before doing a orcid search"
    )
    dialog.run()

    dialog.destroy()


def file_error_window(bibcode):
    dialog = Gtk.MessageDialog(
        flags=0,
        message_type=Gtk.MessageType.ERROR,
        buttons=Gtk.ButtonsType.OK,
        text="Could not download file",
    )
    dialog.format_secondary_text(
        "Could not download "+str(bibcode)
    )
    dialog.run()

    dialog.destroy()

def set_dm(mode=None):
    if mode is None:
        mode = settings.dark_mode
        if mode == 'False':
            mode = False
        else:
            mode = True

    gtksettings = Gtk.Settings.get_default()
    gtksettings.set_property("gtk-application-prefer-dark-theme",mode)
    settings.dark_mode =  mode

def get_dm():
    gtksettings = Gtk.Settings.get_default()
    return gtksettings.get_property("gtk-application-prefer-dark-theme")

def thread(function,*args):
    thread = threading.Thread(target=function,args=args)
    thread.daemon = True
    thread.start()


def save_as(filename, save_func):
    save_dialog = Gtk.FileChooserDialog(title="Save as", transient_for=None,
                                        action=Gtk.FileChooserAction.SAVE)

    save_dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                                        Gtk.STOCK_SAVE, Gtk.ResponseType.ACCEPT)
    # the dialog will present a confirmation dialog if the user types a file name that
    # already exists
    save_dialog.set_do_overwrite_confirmation(True)
    # dialog always on top of the textview window
    save_dialog.set_modal(True)
    f = Gio.File.new_for_path(filename)
    save_dialog.set_file(f)
    # connect the dialog to the callback function save_response_cb()
    save_dialog.connect("response", save_response_cb, save_func)
    # show the dialog
    save_dialog.show()

def save_response_cb(dialog, response_id, save_func):
    save_dialog = dialog
    # if response is "ACCEPT" (the button "Save" has been clicked)
    if response_id == Gtk.ResponseType.ACCEPT:
        f = save_dialog.get_file().get_path()
        # save to file (see below)
        save_func(f)
    # if response is "CANCEL" (the button "Cancel" has been clicked)
    elif response_id == Gtk.ResponseType.CANCEL:
        print("cancelled: FileChooserAction.SAVE")
    # destroy the FileChooserDialog
    dialog.destroy()

def show_status(message,contextid=None):
    if contextid is None:
        contextid = random.randint(1,100000000)

    msg_id = _statusbar.push(contextid, message)

    def func():
        _statusbar.remove(contextid, msg_id)
        return False # Run once

    #Timeout message
    GLib.timeout_add_seconds(5,func)

