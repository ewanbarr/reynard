import urllib2
import time
import logging
from lxml import etree

DEFAULT_URL = "http://pulsarix/info/telescopeStatus.xml"

log = logging.getLogger('reynard.effelsberg.utils')

class TelescopeStatus(object):
    def __init__(self, url=DEFAULT_URL, stale_time=1):
        self.url = url
        self._tree = None
        self._last_update = 0
        self._stale_time = stale_time

    def update_tree(self):
        log.debug("Element tree stale, fetching updated tree.")
        page = urllib2.urlopen("http://pulsarix/info/telescopeStatus.xml")
        self._tree = etree.fromstring(page.read())
        self._last_update = time.time()
        page.close()

    @property
    def tree(self):
        time_since_update = time.time()-self._last_update
        if self._tree is None or time_since_update > self._stale_time:
            self.update_tree()
        return self._tree

    def _fetch(self,name,element):
        return self.tree.xpath("string(TelStat[Name='{name}']/{element}/text())".format(**locals()))

    def get_value(self,name):
        return self._fetch(name,"Value")

    def get_status(self,name):
        return self._fetch(name,"Status")






