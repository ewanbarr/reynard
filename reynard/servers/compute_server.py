import logging
import json
from tornado.gen import coroutine, Return
from katcp import Sensor, AsyncDeviceServer, AsyncReply
from katcp.kattypes import request, return_reply, Int, Str, Discrete
from katcp.resource_client import KATCPClientResource
from katcp.ioloop_manager import with_relative_timeout
from reynard.monitors import DiskMonitor,CpuMonitor,MemoryMonitor
from reynard.pipelines import PIPELINE_REGISTRY, PIPELINE_STATES, PipelineError


class PipelineServer(AsyncDeviceServer):
    VERSION_INFO = ("reynard-pipelineserver-api",0,1)
    BUILD_INFO = ("reynard-pipelineserver-implementation",0,1,"rc1")
    def __init__(self, server_host, server_port, pipeline_type):
        self._pipeline_type = pipeline_type
        self._pipeline = None
        super(PipelineServer,self).__init__(server_host, server_port)

    def setup_sensors(self):
        """Setup sensors."""
        self._pipeline_status = Sensor.discrete("status",
            description = "status of pipeline",
            params = PIPELINE_STATES,
            default = "idle")
        self.add_sensor(self._pipeline_status)

    def start(self):
        self._pipeline = self._pipeline_type()
        self._pipeline.register_callback(lambda state,obj: self._pipeline_status.set_value(state))
        super(PipelineServer,self).start()

    def _async_safe_call(self,req,func):
        @coroutine
        def callback():
            try:
                func()
            except Exception as error:
                req.reply("fail",str(error))
            else:
                req.reply("ok","ok")
        self.ioloop.add_callback(callback)

    @request(Str())
    @return_reply(Str())
    def request_configure(self, req, config):
        """Return available pipelines"""
        self._async_safe_call(req, lambda: self._pipeline.configure(config))
        raise AsyncReply

    @request()
    @return_reply(Str())
    def request_start(self, req):
        """Return available pipelines"""
        self._async_safe_call(req, self._pipeline.start)
        raise AsyncReply

    @request()
    @return_reply(Str())
    def request_stop(self, req):
        """Return available pipelines"""
        self._async_safe_call(req, self._pipeline.stop)
        raise AsyncReply

    @request()
    @return_reply(Str())
    def request_deconfigure(self, req):
        """Return available pipelines"""
        self._async_safe_call(req, self._pipeline.deconfigure)
        raise AsyncReply

    @request()
    @return_reply(Str())
    def request_reset(self, req):
        """Return available pipelines"""
        self._async_safe_call(req, self._pipeline.reset)
        raise AsyncReply

    @request()
    @return_reply(Str())
    def request_status(self, req):
        """Return available pipelines"""
        @coroutine
        def status_getter():
            border = "-"*50
            try:
                status = self._pipeline.status()
            except Exception as error:
                req.reply("fail",str(error))
            else:
                if status.has_key("info"):
                    for container in status["info"]:
                        msg = ("\n"
                            "{border}\n"
                            "Name: {name}\n"
                            "Status: {status}\n"
                            "Logs: \n{logs}\n"
                            "Procs: \n{titles}\n{procs}\n"
                            "{border}\n")
                        msg = msg.format(name=container["name"],
                            status=container["status"],
                            logs=container["logs"],
                            titles="\t".join(container["procs"]["Titles"]),
                            procs="\n".join(["\t".join(info) for info in container["procs"]["Processes"]]),
                            border=border)
                        req.inform(msg)
                req.reply("ok","ok")
        self.ioloop.add_callback(status_getter)
        raise AsyncReply

class PipelineDispatchServer(AsyncDeviceServer):
    VERSION_INFO = ("reynard-pipelinedispatchserver-api",0,1)
    BUILD_INFO = ("reynard-pipelinedispatchserver-implementation",0,1,"rc1")
    def __init__(self, server_host, server_port):
        self._pipeline_servers = {}
        super(PipelineDispatchServer,self).__init__(server_host, server_port)

    def setup_sensors(self):
        """Setup sensors."""
        pass

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
    @return_reply(Str())
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
                req.reply("ok",str(server.bind_address))
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





