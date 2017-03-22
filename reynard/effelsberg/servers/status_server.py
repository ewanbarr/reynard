import logging
import requests
import time
import re
import socket
import select
from lxml import etree
from tornado.gen import coroutine, Return, sleep
from tornado.ioloop import PeriodicCallback
from katcp import Sensor, AsyncDeviceServer, AsyncReply
from katcp.kattypes import request, return_reply, Int, Str, Discrete, Address, Struct
from reynard.utils import doc_inherit

#TELESCOPE_STATUS_URL = "http://pulsarix/info/telescopeStatus.xml"
TELESCOPE_STATUS_URL = "http://localhost:30005/info/telescopeStatus.xml"

JSON_STATUS_MCAST_GROUP = '224.168.2.132'
JSON_STATUS_PORT = 1602

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

class StatusCatcherThread(Thread):
    def __init__(self, mcast_group=JSON_STATUS_MCAST_GROUP, mcast_port=JSON_STATUS_PORT):
        self._mcast_group = mcast_group
        self._mcast_port = mcast_port
        self._sock = None
        self._lock = Lock()
        self._stop_event = Event()
        self._data = None
        Thread.__init__(self)
        self.daemon = True

    @property
    def data(self):
        with self._lock:
            return self._data

    @data.setter
    def data(self,d):
        with self._lock:
            self._data = d

    def start(self):
        self._open_socket()
        Thread.start(self)

    def stop(self):
        self._stop_event.set()
        self._close_socket()

    def run(self):
        data = None
        while not self._stop_event.is_set():
            r,o,e = select.select([self._sock],[],[],0.0)
            if r:
                log.debug("Data in socket... reading data")
                data,_ = self._sock.recvfrom(1<<17)
            else:
                if data is not None:
                    log.debug("Updating data")
                    self.data = json.loads(data)
                log.debug("Sleeping")
                self._stop_event.wait(0.5)

    def _open_socket(self):
        log.debug("Opening socket")
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if hasattr(socket,"SO_REUSEPORT"):
            self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        self._sock.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_TTL, 20)
        self._sock.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_LOOP, 1)
        self._sock.setblocking(0)
        self._sock.bind(('',self._mcast_port))
        intf = socket.gethostbyname(socket.gethostname())
        self._sock.setsockopt(socket.SOL_IP, socket.IP_MULTICAST_IF,
                              socket.inet_aton(intf))
        self._sock.setsockopt(socket.SOL_IP, socket.IP_ADD_MEMBERSHIP,
                              socket.inet_aton(self._mcast_group) + socket.inet_aton(intf))
        log.debug("Socket open")

    def _close_socket(self):
        self._sock.setsockopt(socket.SOL_IP, socket.IP_DROP_MEMBERSHIP,
                              socket.inet_aton(self._mcast_group) + socket.inet_aton('0.0.0.0'))
        self._sock.close()


class JsonStatusServer(AsyncDeviceServer):
    VERSION_INFO = ("reynard-eff-jsonstatusserver-api",0,1)
    BUILD_INFO = ("reynard-eff-jsonstatusserver-implementation",0,1,"rc1")

    def __init__(self, server_host, server_port, mcast_group=JSON_STATUS_MCAST_GROUP, mcast_port=JSON_STATUS_PORT):
        self._mcast_group = mcast_group
        self._mcast_port = mcast_port
        self._catcher_thread = StatusCatcherThread()
        self._monitor = None
        super(JsonStatusServer,self).__init__(server_host, server_port)

    @coroutine
    def _update_sensors(self):
        log.debug("Updating sensor values")
        data = self._catcher_thread.data
        if data is None:
            log.warning("Catcher thread has not received any data yet")
            return
        x, y, z = data["axstatus-0"], data["axstatus-1"], data["axstatus-2"]
        if (x == 32) and (y == 32) and (z == 64):
            self._sensors["status"].set_value("observing")
        else:
            self._sensors["status"].set_value("unknown")

    def start(self):
        """start the server"""
        super(JsonStatusServer,self).start()
        self._catcher_thread.start()
        self._monitor = PeriodicCallback(self._update_sensors,1000,io_loop=self.ioloop)
        self._monitor.start()

    def stop(self):
        """stop the server"""
        if self._monitor:
            self._monitor.stop()
        self._catcher_thread.stop()
        return super(JsonStatusServer,self).stop()

    def setup_sensors(self):
        """Set up basic monitoring sensors.

        Note: These are primarily for testing and
              will be replaced in the final build.
        """
        self.add_sensor(Sensor.string("status",
            description = "The status of the telescope",
            default = "idle",
            initial_status=Sensor.UNKNOWN))


