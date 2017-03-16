import logging
import requests
import time
import re
from lxml import etree
from threading import Lock
from tornado.gen import coroutine, Return
from tornado.ioloop import PeriodicCallback
from katcp import Sensor, AsyncDeviceServer, AsyncReply
from katcp.kattypes import request, return_reply, Int, Str, Discrete, Address, Struct
from katcp.resource_client import KATCPClientResource
from reynard.utils import doc_inherit

log = logging.getLogger('reynard.effelsberg.cam_server')
lock = Lock()

class Config(object):
    backends = {
    "paf":("localhost",1237)
    }
    status_server = ("localhost",1234)

class EffCAMServer(AsyncDeviceServer):
    """The master pulsar backend control server for
    the Effelsberg radio telescope.
    """
    VERSION_INFO = ("reynard-effcamserver-api",0,1)
    BUILD_INFO = ("reynard-effcamserver-implementation",0,1,"rc1")
    DEVICE_STATUSES = ["ok", "degraded", "fail"]

    def __init__(self, server_host, server_port):
        self._config = Config()
        self._backends = {}
        super(EffCAMServer,self).__init__(server_host, server_port)

    def setup_sensors(self):
        """Set up basic monitoring sensors.

        Note: These are primarily for testing and
              will be replaced in the final build.
        """
        self._device_status = Sensor.discrete("device-status",
            description = "Health status of device",
            params = self.DEVICE_STATUSES,
            default = "ok")
        self.add_sensor(self._device_status)
        self._device_armed = Sensor.boolean("device-armed",
            description = "Is the CAM server armed?",
            initial_status = Sensor.NOMINAL,
            default = False)
        self.add_sensor(self._device_armed)

    def start(self):
        super(EffCAMServer,self).start()
        self._setup_clients()
        self._controller = EffController(self._status_server.sensor)

    def _setup_clients(self):
        for name,(ip,port) in self._config.backends.items():
            client = KATCPClientResource(dict(
                name=name,
                address=(ip, port),
                controlled=True))
            client.start()
            self._backends[name]=client
        ip,port = self._config.status_server
        self._status_server = KATCPClientResource(dict(
            name="status-server",
            address=(ip, port),
            controlled=True))
        self._status_server.start()

    @request(Str())
    @return_reply(Address())
    def request_backend_address(self, req, name):
        """request the address of a named backend"""
        if not self._backends.has_key(name):
            raise Exception("No backend with name '{0}'".format(name))
        return ("ok",self._backends[name].bind_address)

    @request()
    @return_reply(Int())
    def request_backend_list(self, req):
        """request a list of connected backends"""
        for name,server in self._backends.items():
            req.inform("{0} {1}".format(name,server.bind_address))
        return ("ok",len(self._backends))

    @request()
    @return_reply(Discrete(DEVICE_STATUSES))
    def request_device_status(self, req):
        """Return the status of the instrument"""
        @coroutine
        def status_query():
            for name,client in self._backends.items():
                status = yield client.sensor.device_status.get_value()
                req.inform("{0} {1}".format(name,status))
            req.reply("ok", "ok")
        self.ioloop.add_callback(status_query)
        raise AsyncReply

    def printit(self,sensor,reading):
        print sensor
        print reading

    @request()
    @return_reply(Str())
    def request_arm(self, req):
        """Arm the controller"""
        self._device_armed.set_value(True)
        self._controller.start()
        return ("ok","armed")

    @request()
    @return_reply(Str())
    def request_disarm(self, req):
        """disarm the controller"""
        self._device_armed.set_value(False)
        self._controller.stop()
        return ("ok","disarmed")

class EffController(object):
    def __init__(self,sensors):
        self.sensors = sensors

    def start(self):
        self.sensors.scannum.set_sampling_strategy('event')
        self.sensors.source.set_sampling_strategy('event')
        self.sensors.subscannum.set_sampling_strategy('event')
        self.sensors.status.set_sampling_strategy('event')
        self.sensors.scannum.register_listener(self.scan_handler)
        log.debug("starting controller")

    def stop(self):
        self.sensors.scannum.unregister_listener(self.scan_handler)
        self.sensors.status.unregister_listener(self.wait_on_not_observing)
        self.sensors.status.unregister_listener(self.wait_on_observing)
        self.sensors.scannum.unregister_listener(self.subscan_handler)
        self.sensors.scannum.set_sampling_strategy('none')
        self.sensors.source.set_sampling_strategy('none')
        self.sensors.subscannum.set_sampling_strategy('none')
        self.sensors.status.set_sampling_strategy('none')
        log.debug("stopping controller")
        log.debug("stopping all active observations")

    @coroutine
    def wait_on_observing(self,rt,t,status,value):
        if value != "Observing":
            return
        log.debug("Telescope entered 'Observing' state: Triggering observation start")
        self.sensors.status.unregister_listener(self.wait_on_observing)
        self.sensors.status.register_listener(self.wait_on_not_observing)
        log.debug("Registering status change handler")

    @coroutine
    def wait_on_not_observing(self,rt,t,status,value):
        log.debug("Telescope state change to '{0}'".format(value))
        log.debug("Deregistering status change handler")
        self.sensors.status.unregister_listener(self.wait_on_not_observing)
        log.debug("Triggering observation stop")

    @coroutine
    def subscan_handler(self,rt,t,status,value):
        log.debug("Subscan number changed: Triggering new observation (same configuration)")
        nsubscans = yield self.sensors.numsubscans.get_value()
        nsubscans = int(nsubscans)
        if int(value) == nsubscans:
            log.debug("Last subscan in set, deregistering subscan handlers")
            self.sensors.subscannum.unregister_listener(self.subscan_handler)
        log.debug("Waiting on 'Observing' status")
        self.sensors.status.register_listener(self.wait_on_observing)

    @coroutine
    def scan_handler(self,rt,t,status,value):
        # Check that previous observation has been completed
        # Deregister any remaining handlers
        # Check number of subscans
        # if more than 1:
        #    Add subscan handler
        # register status change handler
        log.debug("Received new scan number: {0}".format(value))
        log.debug("Deregistering handlers")
        self.sensors.status.unregister_listener(self.wait_on_not_observing)
        self.sensors.status.unregister_listener(self.wait_on_observing)
        self.sensors.scannum.unregister_listener(self.subscan_handler)
        log.debug("Stopping ongoing observations")
        self.scan_number = int(value)
        nsubscans = yield self.sensors.numsubscans.get_value()
        nsubscans = int(nsubscans)
        source_name = yield self.sensors.source.get_value()
        if nsubscans > 1:
            log.debug("Scan has {0} sub scans. Registering subscan handlers.".format(nsubscans))
            self.sensors.subscannum.register_listener(self.subscan_handler)
        self.sensors.status.register_listener(self.wait_on_observing)
        log.debug("Configuring for observation of source {0}".format(source_name))
        log.debug("Waiting on 'Observing' status")



