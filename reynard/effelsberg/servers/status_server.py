import logging
import requests
import time
import re
from lxml import etree
from tornado.gen import coroutine, Return
from tornado.ioloop import PeriodicCallback
from katcp import Sensor, AsyncDeviceServer, AsyncReply
from katcp.kattypes import request, return_reply, Int, Str, Discrete, Address, Struct
from reynard.utils import doc_inherit

TELESCOPE_STATUS_URL = "http://pulsarix/info/telescopeStatus.xml"

log = logging.getLogger('reynard.effelsberg.status_server')

STATUS_MAP = {
    "error":3, # Sensor.STATUSES 'error'
    "norm":1, # Sensor.STATUSES 'nominal'
    "ok":1, # Sensor.STATUSES 'nominal'
    "warn":2 # Sensor.STATUSES 'warn'
}

NON_ASCII_MATCH = re.compile("[^a-zA-Z\d\s.]")

def get_status_xml(url=TELESCOPE_STATUS_URL):
    response = requests.get(url)
    return etree.fromstring(response.content)

def parse_element(element):
    name = element.find("Name").text.encode("utf-8")
    value =  element.find("Value").text.encode("utf-8")
    value = NON_ASCII_MATCH.sub("",value)
    status = element.find("Status")
    if status is not None:
        status_val = STATUS_MAP[status.text.encode("utf-8")]
    else:
        status_val = Sensor.UNKNOWN
    return name,value,status_val


class StatusServer(AsyncDeviceServer):
    VERSION_INFO = ("reynard-eff-statusserver-api",0,1)
    BUILD_INFO = ("reynard-eff-statusserver-implementation",0,1,"rc1")

    def __init__(self, server_host, server_port, status_url=TELESCOPE_STATUS_URL):
        self._url = status_url
        self._timestamp = None
        self._xml_sensors = {}
        self._monitor = None
        super(StatusServer,self).__init__(server_host, server_port)

    @coroutine
    def _update_sensors(self):
        log.debug("Updating sensor values")
        try:
            tree = get_status_xml(self._url)
            for name,sensor in self._xml_sensors.items():
                element = tree.xpath("/TelescopeStatus/TelStat[Name/text()='{0}']".format(name))
                if not element:
                    log.warning("Could not retrieve telescope status for parameter '{0}'".format(name))
                    continue
                name,value,status = parse_element(element[0])
                log.debug("Setting sensor '{name}' to value '{value}' and status '{status}'".format(
                    name=name,value=value,status=status))
                sensor.set(time.time(),status,value)
        except Exception as error:
            log.exception("Error on sensor update")

    def start(self):
        """start the server"""
        super(StatusServer,self).start()
        self._monitor = PeriodicCallback(self._update_sensors, 1000, io_loop=self.ioloop)
        self._monitor.start()

    def setup_sensors(self):
        """Set up basic monitoring sensors.

        Note: These are primarily for testing and
              will be replaced in the final build.
        """
        tree = get_status_xml(self._url)
        elements = tree.xpath("/TelescopeStatus/TelStat")
        for element in elements:
            name,value,status = parse_element(element)
            lower_name = name.lower()
            sensor = Sensor.string("{0}".format(lower_name),
                description = "Value of {0}".format(name),
                default = value,
                initial_status=status)
            self._xml_sensors[name] = sensor
            self.add_sensor(sensor)


