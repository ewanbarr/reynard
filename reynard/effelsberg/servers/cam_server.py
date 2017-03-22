import logging
import requests
import time
import re
from lxml import etree
from tornado.gen import coroutine, Return
from tornado.locks import Lock
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
        self._controller_status = Sensor.discrete("controller-status",
            description = "Status of EffController instance",
            params = EffController.STATES,
            default = "idle")
        self.add_sensor(self._controller_status)

    def start(self):
        super(EffCAMServer,self).start()
        self._setup_clients()
        self._controller = EffController(self)

    def stop(self):
        self._controller.stop()
        self._device_armed.set_value(False)
        return super(EffCAMServer,self).stop()

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

    @request()
    @return_reply(Str())
    def request_arm(self, req):
        """Arm the controller"""
        self._device_armed.set_value(True)
        self.ioloop.add_callback(self._controller.start)
        return ("ok","armed")

    @request()
    @return_reply(Str())
    def request_disarm(self, req):
        """disarm the controller"""
        self._device_armed.set_value(False)
        self.ioloop.add_callback(self._controller.stop)
        return ("ok","disarmed")

class EffController(object):
    STATES = [
    "idle","starting","stopping",
    "waiting_for_scan_number_change",
    "waiting_status_change_to_observe",
    "waiting_status_change_from_observe",
    "configuring_backends",
    "starting_backends",
    "stopping_backends"
    ]

    def __init__(self,cam_server):
        self.cam_server = cam_server
        self.ioloop = cam_server.ioloop
        self.sensors = self.cam_server._status_server.sensor
        self.status = self.cam_server._controller_status

    @coroutine
    def start(self):
        self.status.set_value("starting")
        self.sensors.scannum.set_sampling_strategy('event')
        self.sensors.subscannum.set_sampling_strategy('event')
        self.sensors.status.set_sampling_strategy('event')
        yield self.sensors.scannum.get_value()
        self.sensors.scannum.register_listener(self.scan_handler)
        log.debug("starting controller")
        self.status.set_value("waiting_for_scan_number_change")

    @coroutine
    def stop(self):
        self.status.set_value("stopping")
        self.sensors.scannum.unregister_listener(self.scan_handler)
        self.sensors.status.unregister_listener(self.not_observing_status_handler)
        self.sensors.status.unregister_listener(self.observing_status_handler)
        self.sensors.scannum.unregister_listener(self.subscan_handler)
        self.sensors.scannum.set_sampling_strategy('none')
        self.sensors.subscannum.set_sampling_strategy('none')
        self.sensors.status.set_sampling_strategy('none')
        log.debug("stopping controller")
        log.debug("stopping all active observations")
        self.status.set_value("idle")

    @coroutine
    def observing_status_handler(self,rt,t,status,value):
        if value != "Observing":
            return
        self.status.set_value("starting_backends")
        log.debug("Telescope entered 'Observing' state: Triggering observation start")
        self.sensors.status.unregister_listener(self.observing_status_handler)
        self.sensors.status.register_listener(self.not_observing_status_handler)
        log.debug("Registering status change handler")
        self.status.set_value("waiting_status_change_from_observe")

    @coroutine
    def not_observing_status_handler(self,rt,t,status,value):
        self.status.set_value("stopping_backends")
        log.debug("Telescope state changed to '{0}'".format(value))
        log.debug("Deregistering status change handler")
        self.sensors.status.unregister_listener(self.not_observing_status_handler)
        log.debug("Triggering observation stop")
        self.status.set_value("idle")

    @coroutine
    def subscan_handler(self,rt,t,status,value):
        log.debug("Moved to sub scan {0}".format(value))
        #stop previous
        log.debug("Triggering new observation (same configuration)")
        nsubscans = int(self.sensors.numsubscans.value)
        if int(value) == nsubscans:
            log.debug("Last sub scan in set, deregistering subscan handlers")
            self.sensors.subscannum.unregister_listener(self.subscan_handler)
        log.debug("Waiting on 'Observing' status")
        self.sensors.status.register_listener(self.observing_status_handler)
        self.status.set_value("waiting_status_change_to_observe")

    @coroutine
    def scan_handler(self,rt,t,status,value):
        # Check that previous observation has been completed
        # Deregister any remaining handlers
        # Check number of subscans
        # if more than 1:
        #    Add subscan handler
        # register status change handler
        with (yield lock.acquire()):
            log.debug("Received new scan number: {0}".format(value))
            log.debug("Deregistering handlers")
            self.sensors.status.unregister_listener(self.not_observing_status_handler)
            self.sensors.status.unregister_listener(self.observing_status_handler)
            self.sensors.scannum.unregister_listener(self.subscan_handler)
            log.debug("Stopping any ongoing observations")

            source_name = yield self.sensors.source.get_value()
            receiver = yield self.sensors.receiver.get_value()
            log.debug("Configuring for observation of source '{0}' with receiver '{1}'".format(
                source_name,receiver))
            self.status.set_value("configuring_backends")



            self.scan_number = int(value)
            nsubscans = yield self.sensors.numsubscans.get_value()
            nsubscans = int(nsubscans)
            if nsubscans > 1:
                log.debug("Scan has {0} sub scans. Registering subscan handlers.".format(nsubscans))
                self.sensors.subscannum.register_listener(self.subscan_handler)
            self.sensors.status.register_listener(self.observing_status_handler)
            log.debug("Waiting on 'Observing' status")
            self.status.set_value("waiting_status_change_to_observe")

