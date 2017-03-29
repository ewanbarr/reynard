import logging
import socket
import json
from tornado.gen import coroutine, Return
from katcp import Sensor, AsyncDeviceServer, AsyncReply
from katcp.kattypes import request, return_reply, Int, Str, Discrete
from katcp.resource_client import KATCPClientResource
from katcp.ioloop_manager import with_relative_timeout
from reynard.monitors import DiskMonitor,CpuMonitor,MemoryMonitor
from reynard.utils import doc_inherit, decode_katcp_message, unpack_dict, pack_dict

log = logging.getLogger("reynard.ubi_server")

class UniversalBackendInterface(AsyncDeviceServer):
    """Katcp server for cluster head nodes.

    """
    VERSION_INFO = ("reynard-ubi-api",0,1)
    BUILD_INFO = ("reynard-ubi-implementation",0,1,"rc1")
    DEVICE_STATUSES = ["ok","fail","degraded"]

    def __init__(self, server_host, server_port):
        self._nodes = {}
        super(UniversalBackendInterface,self).__init__(server_host, server_port)

    def setup_sensors(self):
        """add sensors"""
        pass

    def start(self):
        """Start the server

        Based on the passed configuration object this is
        where the clients for suboridnates nodes will be
        set up.
        """
        super(UniversalBackendInterface,self).start()

    def _add_node(self,name,ip,port):
        """Add a named node."""
        if name in self._nodes.keys():
            raise KeyError("Node already added with name '{name}'".format(name=name))
        client = KATCPClientResource(dict(
            name=name,
            address=(ip, port),
            controlled=True))
        client.start()
        self._nodes[name]=client

    def _remove_node(self,name):
        """Remove a client by name."""
        if name not in self._nodes.keys():
            raise KeyError("No node exists with name '{name}'".format(name=name))
        self._nodes[name].stop()
        del self._nodes[name]

    @request(Str(),Str())
    @return_reply(Str(),Str())
    def request_configure(self, req, config, sensors):
        """config"""
        @coroutine
        def configure(config):
            for node in config["nodes"]:
                for name,client in self._nodes.items():
                    if client.address == (node["ip"],node["port"]):
                        print "Node found with name '{0}'".format(name)
                        print "---------------"
                        print node["pipelines"]
                        print "---------------"
                        response = yield client.req.configure(pack_dict(node["pipelines"]),sensors)
                        print response
                        break
                else:
                    print "No node found at address {0}".format((node["ip"],node["port"]))
                print "FROM UBI"
                print node
            req.reply("ok","configured")

        print unpack_dict(config)
        print unpack_dict(sensors)
        self.ioloop.add_callback(lambda: configure(unpack_dict(config)))
        raise AsyncReply

    @request()
    @return_reply(Str())
    def request_start(self, req):
        """start"""
        @coroutine
        def start():
            pass
        raise AsyncReply

    @request()
    @return_reply(Str())
    def request_stop(self, req):
        """stop"""
        @coroutine
        def stop():
            pass
        raise AsyncReply

    @request()
    @return_reply(Str())
    def request_deconfigure(self, req):
        """deconfig"""
        @coroutine
        def deconfigure():
            pass
        raise AsyncReply

    @request(Str(),Str(),Int())
    @return_reply(Str())
    def request_node_add(self, req, name, ip, port):
        """Add a new node."""
        try:
            self._add_node(name,ip,port)
        except KeyError,e:
            return ("fail",str(e))
        return ("ok","added node")

    @request(Str())
    @return_reply(Str())
    def request_node_remove(self, req, name):
        """Add a new node."""
        try:
            self._remove_node(name)
        except KeyError,e:
            return ("fail",str(e))
        return ("ok","removed node")

    @request()
    @return_reply(Str())
    def request_node_list(self, req):
        """List all available nodes"""
        msg = [""]
        for ii,(name,node) in enumerate(self._nodes.items()):
            msg.append("{node.name} {node.address}".format(node=node))
        req.inform("\n\_\_\_\_".join(msg))
        return ("ok","{count} nodes found".format(count=len(self._nodes)))

    @request()
    @return_reply(Discrete(DEVICE_STATUSES))
    def request_device_status(self, req):
        """Return status of the instrument.

        Notes: Status is based on aggregate information
               from all subordinate nodes.

        Currently this is a dummy function to test chaining
        async calls.
        """
        @coroutine
        def status_handler():
            futures = {}
            for name,client in self._nodes.items():
                future = client.req.device_status()
                futures[name] = future
            statuses = {}
            for name,future in futures.items():
                with_relative_timeout(2,future)
                status = yield future
                if not status:
                    req.inform("Warning {name} status request failed: {msg}".format(
                        name=name,msg=str(status)))
                reply = status.reply
                status_message = reply.arguments[1]
                req.inform("Client {name} state: {msg}".format(
                    name=name,msg=status_message))
                statuses[name] = reply.arguments[1] == "ok"
            passes = [success for name,success in statuses.items()]
            if all(passes):
                req.reply("ok","ok")
            else:
                # some policy for degradation needs to be determined based on
                # overall instrument capability. Maybe fraction of beams x bandwidth?
                fail_count = len(passes)-sum(passes)
                if fail_count > 1:
                    req.reply("ok","fail")
                else:
                    req.reply("ok","degraded")

        self.ioloop.add_callback(status_handler)
        raise AsyncReply

