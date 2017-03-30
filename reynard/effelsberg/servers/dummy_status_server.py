import logging
import requests
import time
import re
import socket
import select
import json
from lxml import etree
from threading import Thread, Event, Lock
from tornado.gen import coroutine, Return, sleep
from tornado.ioloop import PeriodicCallback
from katcp import Sensor, AsyncDeviceServer, AsyncReply
from katcp.kattypes import request, return_reply, Int, Str, Discrete, Address, Struct
from reynard.utils import doc_inherit
from reynard.utils import escape_string, pack_dict
from reynard.effelsberg.servers import EFF_JSON_CONFIG

log = logging.getLogger('reynard.effelsberg.dummy_status_server')

TYPE_CONVERTER = {
    "float":float,
    "int":int,
    "string":str,
    "bool":int
}

class DummyJsonStatusServer(AsyncDeviceServer):
    VERSION_INFO = ("reynard-eff-dummy-jsonstatusserver-api",0,1)
    BUILD_INFO = ("reynard-eff-dummy-jsonstatusserver-implementation",0,1,"rc1")

    def __init__(self, server_host, server_port, parser=EFF_JSON_CONFIG):
        self._parser = parser
        super(DummyJsonStatusServer,self).__init__(server_host, server_port)

    def setup_sensors(self):
        """Set up basic monitoring sensors.

        Note: These are primarily for testing and
              will be replaced in the final build.
        """
        for name,params in self._parser.items():
            if params["type"] == "float":
                sensor = Sensor.float(name,
                    description = params["description"],
                    unit = params.get("units",None),
                    default = params.get("default",0.0),
                    initial_status=Sensor.UNKNOWN)
            elif params["type"] == "string":
                sensor = Sensor.string(name,
                    description = params["description"],
                    default = params.get("default",""),
                    initial_status=Sensor.UNKNOWN)
            elif params["type"] == "int":
                sensor = Sensor.integer(name,
                    description = params["description"],
                    default = params.get("default",0),
                    unit = params.get("units",None),
                    initial_status=Sensor.UNKNOWN)
            elif params["type"] == "bool":
                sensor = Sensor.boolean(name,
                    description = params["description"],
                    default = params.get("default",False),
                    initial_status=Sensor.UNKNOWN)
            else:
                raise Exception("Unknown sensor type '{0}' requested".format(params["type"]))
            self.add_sensor(sensor)

    @request(Str(),Str())
    @return_reply(Str())
    def request_sensor_set(self, req, name, value):
        """Set the value of a sensor"""
        if not self._parser.has_key(name):
            return ("fail","invalid sensor name")
        try:
            param = self._parser[name]
            value = TYPE_CONVERTER[param["type"]](value)
            self._sensors[name].set_value(value)
        except Exception as error:
            return ("fail",str(error))
        else:
            return ("ok","status set to {0}".format(self._sensors[name].value()))

    @request()
    @return_reply(Str())
    def request_json(self,req):
        """request an JSON version of the status message"""
        out = {}
        for name,sensor in self._sensors.items():
            out[name] = sensor.value()
        return ("ok",pack_dict(out))



