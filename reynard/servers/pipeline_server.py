import logging
from tornado.gen import coroutine
from katcp import Sensor, AsyncDeviceServer, AsyncReply
from katcp.kattypes import request, return_reply, Str
from reynard.pipelines import PIPELINE_STATES
from reynard.utils import doc_inherit, unpack_dict

log = logging.getLogger("reynard.pipeline_server")


class PipelineServer(AsyncDeviceServer):
    VERSION_INFO = ("reynard-pipelineserver-api", 0, 1)
    BUILD_INFO = ("reynard-pipelineserver-implementation", 0, 1, "rc1")

    def __init__(self, server_host, server_port, pipeline_type):
        self._pipeline_type = pipeline_type
        self._pipeline = None
        super(PipelineServer, self).__init__(server_host, server_port)

    @doc_inherit
    def setup_sensors(self):
        self._pipeline_status = Sensor.discrete(
            "status",
            description="status of pipeline",
            params=PIPELINE_STATES,
            default="idle")
        self.add_sensor(self._pipeline_status)

    def start(self):
        self._pipeline = self._pipeline_type()
        self._pipeline.register_callback(
            lambda state, obj: self._pipeline_status.set_value(state))
        super(PipelineServer, self).start()

    def _async_safe_call(self, req, func):
        @coroutine
        def callback():
            try:
                func()
            except Exception as error:
                req.reply("fail", str(error))
            else:
                req.reply("ok", "ok")
        self.ioloop.add_callback(callback)

    @request(Str(), Str())
    @return_reply(Str())
    def request_configure(self, req, config, sensors):
        """Return available pipelines"""
        try:
            config = unpack_dict(config)
            sensors = unpack_dict(sensors)
        except Exception as error:
            return ("fail", str(error))
        self._async_safe_call(
            req, lambda: self._pipeline.configure(
                config, sensors))
        raise AsyncReply

    @request(Str())
    @return_reply(Str())
    def request_start(self, req, sensors):
        """Return available pipelines"""
        try:
            sensors = unpack_dict(sensors)
        except Exception as error:
            return ("fail", str(error))
        self._async_safe_call(req, lambda: self._pipeline.start(sensors))
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
            border = "-" * 50
            try:
                status = self._pipeline.status()
            except Exception as error:
                req.reply("fail", str(error))
            else:
                if "info" in status:
                    for container in status["info"]:
                        msg = ("\n"
                               "{border}\n"
                               "Name: {name}\n"
                               "Status: {status}\n"
                               "Logs: \n{logs}\n"
                               "Procs: \n{titles}\n{procs}\n"
                               "{border}\n")
                        msg = msg.format(
                            name=container["name"],
                            status=container["status"],
                            logs=container["logs"],
                            titles="\t".join(container["procs"]["Titles"]),
                            procs="\n".join(
                                ["\t".join(info)
                                 for info in container["procs"]
                                 ["Processes"]]),
                            border=border)
                        req.inform(msg)
                req.reply("ok", "ok")
        self.ioloop.add_callback(status_getter)
        raise AsyncReply
