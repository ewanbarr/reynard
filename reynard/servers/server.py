import logging
from tornado.gen import coroutine, Return
from katcp import Sensor, AsyncDeviceServer, AsyncReply
from katcp.kattypes import request, return_reply, Int, Str, Discrete
from katcp.resource_client import KATCPClientResource
from katcp.ioloop_manager import with_relative_timeout
from reynard.monitors import DiskMonitor,CpuMonitor,MemoryMonitor

log = logging.getLogger("reynard.server")

class NodeServer(AsyncDeviceServer):
    """Basic katcp server providing common sensors
       for monitoring a node.
    """
    VERSION_INFO = ("reynard-nodeserver-api",0,1)
    BUILD_INFO = ("reynard-nodeserver-implementation",0,1,"rc1")
    DEVICE_STATUSES = ["ok", "degraded", "fail"]

    def __init__(self, server_host, server_port, config):
        self._config = config
        self._monitors = {}
        super(NodeServer,self).__init__(server_host, server_port)

    @request()
    @return_reply(Discrete(DEVICE_STATUSES))
    def request_device_status(self, req):
        """Return the status of the instrument"""

        def status_query():
            # go and find out the status of all
            # subordinates.
            req.reply("ok", "degraded")

        self.ioloop.add_callback(status_query)
        raise AsyncReply

    def setup_sensors(self):
        """Set up basic monitoring sensors.

        Note: These are primarily for testing and
              will be replaced in the final build.
        """
        self._device_status = Sensor.discrete("device-status",
            description = "health status of node",
            params = self.DEVICE_STATUSES,
            default = "ok")
        self.add_sensor(self._device_status)
        self._monitors["disk"] = DiskMonitor(self._config.VOLUMES)
        self._monitors["cpu"] = CpuMonitor()
        self._monitors["memory"] = MemoryMonitor()
        for monitor in self._monitors.values():
            for sensor in monitor.sensors():
                self.add_sensor(sensor)
            monitor.start()


class ManagementNode(NodeServer):
    """Katcp server for cluster head nodes.

    Notes: This is the basis of the top level
           interface for FBF/APSUSE.
    """
    VERSION_INFO = ("reynard-managementnode-api",0,1)
    BUILD_INFO = ("reynard-managementnode-implementation",0,1,"rc1")

    def __init__(self, server_host, server_port, config):
        self._clients = {}
        super(ManagementNode,self).__init__(server_host, server_port, config)

    def start(self):
        """Start the server

        Based on the passed configuration object this is
        where the clients for suboridnates nodes will be
        set up.
        """
        super(ManagementNode,self).start()
        self.ioloop.add_callback(self._setup_clients)

    def _setup_clients(self):
        """Setup clients based on configuration object."""
        for node,port in self._config.NODES:
            name = '{node}-client'.format(node=node)
            self._add_client(name,'127.0.0.1', port)

    def _add_client(self,name,ip,port):
        """Add a named client."""
        if name in self._clients.keys():
            raise KeyError("Client already exists with name '{name}'".format(name=name))
        client = KATCPClientResource(dict(
            name=name,
            address=(ip, port),
            controlled=True))
        client.start()
        self._clients[name]=client

    def _remove_client(self,name):
        """Remove a client by name."""
        if name not in self._clients.keys():
            raise KeyError("No client exists with name '{name}'".format(name=name))
        self._clients[name].stop()
        self._clients[name].join()
        del self._clients[name]

    @request(Str(),Str(),Int())
    @return_reply(Str())
    def request_client_add(self, req, name, ip, port):
        """Add a new client."""
        try:
            self._add_client(name,ip,port)
        except KeyError,e:
            return ("fail",str(e))
        return ("ok","added client")

    @request()
    @return_reply(Str())
    def request_client_list(self, req):
        """List all available clients"""
        msg = [""]
        for ii,(name,client) in enumerate(self._clients.items()):
            msg.append("{client.name} {client.address}".format(client=client))
        req.inform("\n\_\_\_\_".join(msg))
        return ("ok","{count} clients found".format(count=len(self._clients)))

    @request()
    @return_reply(Discrete(NodeServer.DEVICE_STATUSES))
    def request_device_status(self, req):
        """Return status of the instrument.

        Notes: Status is based on aggregate information
               from all subordinate client.

        Currently this is a dummy function to test chaining
        async calls.
        """
        @coroutine
        def status_handler():
            futures = {}
            for name,client in self._clients.items():
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

