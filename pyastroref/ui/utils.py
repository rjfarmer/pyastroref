# SPDX-License-Identifier: GPL-2.0-or-later

import os
import sys
import threading

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk, GObject, Gdk, Gio

from ..papers import utils


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


def set_dm(mode=None):
    if mode is None:
        mode = utils.read_key_file(utils.settings['DARK_MODE_FILE'])
        if mode == 'False':
            mode = False
        else:
            mode = True

    settings = Gtk.Settings.get_default()
    settings.set_property("gtk-application-prefer-dark-theme",mode)
    utils.save_key_file(utils.settings['DARK_MODE_FILE'], mode)

def get_dm():
    settings = Gtk.Settings.get_default()
    print(settings.get_property("gtk-application-prefer-dark-theme"))
    return settings.get_property("gtk-application-prefer-dark-theme")

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