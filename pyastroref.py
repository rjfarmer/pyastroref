import threading
import time
import os
import adsabs

import gi

gi.require_version("Gtk", "3.0")
gi.require_version('EvinceDocument', '3.0')
gi.require_version('EvinceView', '3.0')

from gi.repository import GLib, Gtk, GObject, Gio

from gi.repository import EvinceDocument
from gi.repository import EvinceView

EvinceDocument.init()


class MyWindow(Gtk.Window):
    def __init__(self):
        self.settings = {}
        self.pages = {}

        Gtk.Window.__init__(self, title="pyAstroRef")

        self.setup_headerbar()
        self.setup_search_bar()
        self.setup_notebook()
        self.setup_grid()       


    def on_click_load_options(self, button):
        win = OptionsMenu()
        win.show_all()

    def on_click_search(self, button):
        query = self.search.get_text()

        if len(query) == 0:
            return

        self.new_page(query)


    def new_page(self,filename):

        if filename in self.pages:
            if self.pages[filename].page_num >= 0:
                self.notebook.set_current_page(self.pages[filename].page_num)
                return
        
        self.pages[filename] = pdfPage(self.notebook,'/data/Insync/refs/papers/'+filename+'.pdf')

        page = self.pages[filename]
        index = self.notebook.append_page(page.add_page(),page.make_header())
        page.page_num = index
        self.notebook.set_tab_reorderable(page.page, True)
        self.notebook.show_all()


    def setup_search_bar(self):
        self.search = Gtk.SearchEntry()
        self.search.set_width_chars(100)
        self.search.connect("activate",self.on_click_search)

        self.search.set_can_default(True)
        self.set_default(self.search)
        self.search.set_hexpand(True)

    def setup_headerbar(self):
        self.button_opt = Gtk.Button()
        self.button_opt.connect("clicked", self.on_click_load_options)
        image = Gtk.Image()
        image.set_from_icon_name('open-menu-symbolic', Gtk.IconSize.BUTTON)
        self.button_opt.set_image(image)

        hb = Gtk.HeaderBar()
        hb.set_show_close_button(True)
        hb.props.title = "pyAstroRef"
        self.set_titlebar(hb)

        hb.pack_start(self.button_opt)

    def setup_notebook(self):
        self.notebook = Gtk.Notebook()
        self.notebook.set_hexpand(True)
        self.notebook.set_vexpand(True)
        self.notebook.set_tab_pos(Gtk.PositionType.LEFT)
        
    def setup_grid(self):
        self.grid = Gtk.Grid()
        self.add(self.grid)

        self.grid.add(self.search)
        self.grid.attach_next_to(self.notebook,self.search,
                             Gtk.PositionType.BOTTOM,1,1) 


class pdfPage(object):
    def __init__(self, notebook, filename):
        self._filename = filename
        self.filename = 'file://'+filename
        self.doc = EvinceDocument.Document.factory_get_document(self.filename)

        self.arixv = None
        self.page = None
        self.notebook = notebook
        self.page_num = -1


    def add_page(self):

        page = Gtk.Box()
        page.set_border_width(10)
        page.pack_start(
                self.show_pdf(),
                True,True,0
            )
        self.page = page
        return page

    def make_header(self):
        header = Gtk.HBox()
        title_label = self.name()
        image = Gtk.Image()
        image.set_from_icon_name('gtk-close', Gtk.IconSize.BUTTON)
        close_button = Gtk.Button()
        close_button.set_image(image)
        close_button.set_relief(Gtk.ReliefStyle.NONE)
        close_button.connect('clicked', self.on_tab_close)
        header.pack_start(title_label,
                          expand=True, fill=True, padding=0)
        header.pack_end(close_button,
                        expand=False, fill=False, padding=1)
        header.show_all()

        return header

    def on_tab_close(self, button):
        self.notebook.remove_page(self.page_num)
        self.page_num = -1


    def show_pdf(self):
       scroll = Gtk.ScrolledWindow()
       view = EvinceView.View()
       model = EvinceView.DocumentModel()
       model.set_document(self.doc)
       view.set_model(model)
       scroll.add(view)
       return scroll  

    def name(self):
        return Gtk.Label(label=os.path.basename(self.filename))

    def arixv_num(self):
        page = self.doc.get_page(0)
        text = self.doc.get_text(page)

        for i in text.split('\n'):
            if 'arXiv:' in i :
                self.arixv = i.split()[0][len('arXiv:'):]

    def get_details(self):
        if self.arixv is None:
            self.arixv_num()

        


class OptionsMenu(Gtk.Window):
    def __init__(self):
        Gtk.Window.__init__(self, title="Options")

        grid = Gtk.Grid()
        self.add(grid)

        self.ads_entry = Gtk.Entry()
        self.ads_entry.set_width_chars(50)
        self.ads_entry.set_text(adsabs.load_adskey())

        self.orcid_entry = Gtk.Entry()
        self.orcid_entry.set_text(adsabs.load_orcidkey())
        self.orcid_entry.set_width_chars(50)

        self.folder_entry = Gtk.Button(label="Choose Folder")
        self.folder_entry.connect("clicked", self.on_file_clicked)

        ads_label = Gtk.Label(label='ADSABS ID')
        orcid_label = Gtk.Label(label='ORCID ID')
        file_label = Gtk.Label(label='Save folder')

        save_button_ads = Gtk.Button(label="Save")
        save_button_ads.connect("clicked", self.save_ads)

        save_button_orcid = Gtk.Button(label="Save")
        save_button_orcid.connect("clicked", self.save_orcid)

        grid.add(ads_label)
        grid.attach_next_to(self.ads_entry,ads_label,
                            Gtk.PositionType.RIGHT,1,1)
        grid.attach_next_to(save_button_ads,self.ads_entry,
                            Gtk.PositionType.RIGHT,1,1)        

        grid.attach_next_to(orcid_label,ads_label,
                            Gtk.PositionType.BOTTOM,1,1)
        grid.attach_next_to(self.orcid_entry,orcid_label,
                            Gtk.PositionType.RIGHT,1,1)
        grid.attach_next_to(save_button_orcid,self.orcid_entry,
                            Gtk.PositionType.RIGHT,1,1)  

        grid.attach_next_to(file_label,orcid_label,
                            Gtk.PositionType.BOTTOM,1,1)
        grid.attach_next_to(self.folder_entry,file_label,
                            Gtk.PositionType.RIGHT,1,1)        

    def save_ads(self, button):
        value = self.ads_entry.get_text()
        adsabs.save_adskey(value)

    def save_orcid(self, button):
        value = self.orcid_entry.get_text()
        adsabs.save_orcidkey(value)    



    def on_file_clicked(self, widget):
        dialog = Gtk.FileChooserDialog(
            title="Please choose a folder", parent=self, action=Gtk.FileChooserAction.SELECT_FOLDER
        )
        dialog.add_buttons(
            Gtk.STOCK_CANCEL,
            Gtk.ResponseType.CANCEL,
            Gtk.STOCK_OPEN,
            Gtk.ResponseType.OK,
        )

        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            widget.set_label(dialog.get_filename())
            
        dialog.destroy()

if __name__ == "__main__":
    win = MyWindow()
    win.connect("destroy", Gtk.main_quit)
    win.set_hide_titlebar_when_maximized(False)
    win.maximize()
    win.show_all()
    Gtk.main()
