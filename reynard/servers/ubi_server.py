import logging
from tornado.gen import coroutine, Return
from katcp import Sensor, AsyncDeviceServer, AsyncReply
from katcp.kattypes import request, return_reply, Int, Str, Discrete
from katcp.resource_client import KATCPClientResource
from katcp.ioloop_manager import with_relative_timeout
from reynard.monitors import DiskMonitor,CpuMonitor,MemoryMonitor
from reynard.utils import doc_inherit

log = logging.getLogger("reynard.ubi_server")

class UniversalBackendInterface(AsyncDeviceServer):
    """Katcp server for cluster head nodes.

    Notes: This is the basis of the top level
           interface for FBF/APSUSE.
    """
    VERSION_INFO = ("reynard-ubi-api",0,1)
    BUILD_INFO = ("reynard-ubi-implementation",0,1,"rc1")
    DEVICE_STATUSES = ["ok","fail","degraded"]

    def __init__(self, server_host, server_port, config):
        self._nodes = {}
        super(ManagementNode,self).__init__(server_host, server_port)

    def setup_sensors(self):
        """add sensors"""
        pass

    def start(self):
        """Start the server

        Based on the passed configuration object this is
        where the clients for suboridnates nodes will be
        set up.
        """
        super(ManagementNode,self).start()
        self.ioloop.add_callback(self._setup_nodes)

    def _setup_nodes(self):
        """Setup nodes based on configuration object."""
        for node,port in self._config.NODES:
            self._add_node(node,'127.0.0.1', port)

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
        self._nodes[name].join()
        del self._nodes[name]

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
            self._remove_node(name,ip,port)
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

