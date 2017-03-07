"""
Control server for PAF instrument.

Is provided with telescope status information from XML status message.
Gets commands from either a CLI or from a script run by the control webpage.
Sends control messages to PAF management server.
Gets status information from PAF management server.
"""
import logging
from tornado.gen import coroutine, Return
from katcp import Sensor, AsyncDeviceServer, AsyncReply
from katcp.kattypes import request, return_reply, Int, Str, Discrete
from katcp.resource_client import KATCPClientResource

log = logging.getLogger('reynard.effelsberg.paf.servers')

class PafInterfaceServer(AsyncDeviceServer):
    def __init__(self, server_host, server_port, paf_ip="", paf_port=0):
        super(PafInterfaceServer,self).__init__(server_host, server_port)
        self.paf_ip = paf_ip
        self.paf_port = paf_port
        self.paf_client = None

    def setup_sensors(self):
        pass

    def start(self):
        super(PafInterfaceServer,self).start()
        #self.paf_client = KATCPClientResource(dict(
        #    name="paf",
        #    address=(self.paf_ip, self.paf_port),
        #    controlled=True))
        #self.paf_client.start()

    @request()
    @return_reply(Str())
    def request_arm(self, req):
        """Return the status of the instrument"""

        @coroutine
        def arm_query():
            req.reply("ok","armed")

        self.ioloop.add_callback(arm_query)
        raise AsyncReply

    @request()
    @return_reply(Str())
    def request_disarm(self, req):
        """Return the status of the instrument"""

        @coroutine
        def disarm_query():
            req.reply("ok","disarmed")

        self.ioloop.add_callback(disarm_query)
        raise AsyncReply

    @request(Str())
    @return_reply(Str())
    def request_configure(self, req, config):
        """Return the status of the instrument"""

        @coroutine
        def configure_query():
            req.reply("ok","configured")

        self.ioloop.add_callback(configure_query)
        raise AsyncReply


