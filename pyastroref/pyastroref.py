# SPDX-License-Identifier: GPL-2.0-or-later

import sys,os
import argparse

import threading
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk

from .ui import main as main_win


def main():
    win = main_win.MainWindow()
    win.connect("destroy", Gtk.main_quit)
    win.set_hide_titlebar_when_maximized(False)
    win.set_position(Gtk.WindowPosition.CENTER)
    win.maximize()
    win.show_all()
    Gtk.main()

def commandline():
    parser = argparse.ArgumentParser()
    args = parser.parse_args()

if __name__ == "__main__":
    commandline()
    main()





