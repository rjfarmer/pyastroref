# SPDX-License-Identifier: GPL-2.0-or-later

import os
import re
import requests
import datetime
from pathlib import Path
import feedparser

from . import articles

class arxivrss(object):
    def __init__(self, adsdata):
        self.url = 'http://export.arxiv.org/rss/astro-ph'
        self._feed = None
        self.adsdata = adsdata
        self._data = []

    def articles(self):
        if self._feed is None:
            self._feed = feedparser.parse(self.url)
            arxiv_ids = [i['id'].split('/')[-1] for i in self._feed['entries']]

            # Filter resubmissions out
            today=datetime.date.today()
            thismonth = str(today.year-2000)+str(today.month).zfill(2)
            arxiv_ids = [i for i in arxiv_ids if i.startswith(thismonth)]

            self._data = articles.search(self.adsdata).arxiv_multi(arxiv_ids)

        return self._data