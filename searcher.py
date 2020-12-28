import textwrap

import PyQt5.QtWidgets as QtWidgets
import PyQt5.QtGui as QtGui
import PyQt5.QtCore as QtCore

import pyastroref.search.adsabs as adsabs
import pyastroref.search.downloader as downloader

class searchTab(QtWidgets.QListWidget):
    def __init__(self, query,parent=None):
        super().__init__(parent)
        self._parent = parent
        self.query = query
        self.name = query
        self._items = []
        self.results = []
        self._init()
        
    def _init(self):
        self.setGeometry(0,0,
                        self._parent.frameGeometry().width(),
                        self._parent.frameGeometry().height()
                        )
        self.itemDoubleClicked.connect(self.item_click)

    def load(self):
        # if self.query is 'all':
        searcher = adsabs.search()
        results = searcher.search(self.query)
        
        idx=0
        for i in results:
            self.results.append(i)
            name = i['title'][0]
            name = name + ' '
            len_a = len(i['author'])
            
            suffix = ''
            if len_a>3:
                suffix = 'et al '
            
            for j in i['author'][:min(len_a,3)]:
                name = name + str(j)+"; " 
            name = name + suffix
            name = name + str(i['year'])
            
            name = name + ' '+ str(i['pub'])
            self._items.append(QtWidgets.QListWidgetItem(name,self))
            self._items[-1]._index = idx
            
            if i['abstract'] is not None:
                tooltip = "\n".join([i for i in textwrap.wrap(i['abstract'])])
            else:
                tooltip = 'No abstract available'
            
            self._items[-1].setToolTip(tooltip)
            self.addItem(self._items[-1])
            
            idx = idx +1
            
        if idx==0:
            x = QtWidgets.QListWidgetItem("No results found",self)
            x._index = -1
            self.addItem(x)

    def item_click(self, item):
        index = item._index
        if index < 0:
            return
        
        article = self.results[index]
        
        d = downloader.download(article['bibcode'],article['identifier'])
        d.find_arixv() 
        fd = d.download()
        try:
            fd = fd.decode()
        except AttributeError:
            pass
        if fd is not None:
            self._parent.add_tab(data=fd,extras=article,
                                tab_type='pdf')
    
        
