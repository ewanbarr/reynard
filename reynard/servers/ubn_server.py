import logging
from tornado.gen import coroutine, Return
from katcp import Sensor, AsyncDeviceServer, AsyncReply
from katcp.kattypes import request, return_reply, Int, Str, Discrete, Address
from katcp.resource_client import KATCPClientResource
from katcp.ioloop_manager import with_relative_timeout
from tornado.ioloop import PeriodicCallback
from reynard.monitors import DiskMonitor,CpuMonitor,MemoryMonitor
from reynard.utils import doc_inherit

log = logging.getLogger("reynard.ubn_server")

class UniversalBackendNode(AsyncDeviceServer):
    VERSION_INFO = ("reynard-ubn-api",0,1)
    BUILD_INFO = ("reynard-ubn-implementation",0,1,"rc1")
    def __init__(self, server_host, server_port):
        self._pipeline_servers = {}
        super(UniversalBackendNode,self).__init__(server_host, server_port)

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
        self._monitors["disk"] = DiskMonitor([("root","/"),])
        self._monitors["cpu"] = CpuMonitor()
        self._monitors["memory"] = MemoryMonitor()
        for monitor in self._monitors.values():
            for sensor in monitor.sensors():
                self.add_sensor(sensor)

    def start(self):
        super(UniversalBackendNode,self).__init__()
        for monitor in self._monitors.values():
            monitor.start(1000,self.ioloop)

    def stop(self):
        for monitor in self._monitors.values():
            monitor.stop()
        return super(UniversalBackendNode,self).stop()

    @request()
    @return_reply(Str())
    def request_pipeline_avail(self, req):
        """Return available pipelines"""
        for name,info in PIPELINE_REGISTRY.items():
            border = "-"*50
            msg = ("\n"+border+"\n"
                "Name: {name}\n"
                "Requires Nvidia support: {requires_nvidia}\n"
                "Description:\n{description}\n").format(name=name,**info)
            req.inform(msg)
        response = json.dumps(PIPELINE_REGISTRY.keys())
        return ("ok",response)

    @request(Str(),Str())
    @return_reply(Address())
    def request_pipeline_create(self, req, name, pipeline_name):
        """Create a PipelineServer instance"""
        @coroutine
        def create_pipeline_server():
            if PIPELINE_REGISTRY.has_key(pipeline_name):
                pipeline_type = PIPELINE_REGISTRY[pipeline_name]["class"]
                server = PipelineServer("localhost",0,pipeline_type)
                self._pipeline_servers[name] = server
                #self.ioloop.add_callback(server.start)
                #self.ioloop.add_callback(lambda: req.reply("ok",str(server.bind_address)))
                server.start()
                req.inform("Server started at {0}:{1}".format(*server.bind_address))
                req.reply("ok",Address(server.bind_address))
            else:
                req.reply("fail","No pipeline named '{0}' available".format(pipeline_name))
        self.ioloop.add_callback(create_pipeline_server)
        raise AsyncReply

    @request()
    @return_reply(Int())
    def request_pipeline_list(self, req):
        """List running pipeline servers"""
        msg = "\nName\tAddress\n"
        for name,server in self._pipeline_servers.items():
            msg += "{0}\t{1}".format(name,server.bind_address)
        req.inform(msg+"\n")
        return ("ok",len(self._pipeline_servers.keys()))

    @request(Str())
    @return_reply(Str())
    def request_pipeline_destroy(self, req, name):
        """Create a PipelineServer instance"""
        if name in self._pipeline_servers.keys():
            server = self._pipeline_servers[name]
            self.ioloop.add_callback(server.stop)
            return ("ok","ok")
        else:
            return ("fail","No pipeline named '{0}'".format(name))
