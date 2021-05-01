# SPDX-License-Identifier: GPL-2.0-or-later

import os
import sys
import threading

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk, GObject, Gdk

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
        "Please set upi orcid before doing a orcid search"
    )
    dialog.run()

    dialog.destroy()