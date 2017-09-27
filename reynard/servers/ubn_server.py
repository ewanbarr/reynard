import logging
import json
from tornado.gen import coroutine
from katcp import Sensor, AsyncDeviceServer, AsyncReply
from katcp.kattypes import request, return_reply, Int, Str
from katcp.resource_client import KATCPClientResource
from reynard.monitors import DiskMonitor, CpuMonitor, MemoryMonitor
from reynard.utils.katcp import unpack_dict, pack_dict
from reynard.pipelines import PIPELINE_REGISTRY
from reynard.servers import PipelineServer

log = logging.getLogger("reynard.ubn_server")


class PipelineNameExists(Exception):
    pass


class InvalidPipeline(Exception):
    pass


class ClientExists(Exception):
    pass


class UniversalBackendNode(AsyncDeviceServer):
    VERSION_INFO = ("reynard-ubn-api", 0, 1)
    BUILD_INFO = ("reynard-ubn-implementation", 0, 1, "rc1")
    DEVICE_STATUSES = ["ok", "fail", "degraded"]

    def __init__(self, server_host, server_port):
        self._pipeline_servers = {}
        self._pipeline_clients = {}
        self._monitors = {}
        super(UniversalBackendNode, self).__init__(server_host, server_port)

    def setup_sensors(self):
        """Set up basic monitoring sensors.

        Note: These are primarily for testing and
              will be replaced in the final build.
        """
        self._device_status = Sensor.discrete(
            "device-status", description="health status of node",
            params=self.DEVICE_STATUSES, default="ok")
        self._active = Sensor.boolean(
            "active",
            description="Is node configured for processing",
            default=False)
        self.add_sensor(self._device_status)
        self.add_sensor(self._active)
        self._monitors["disk"] = DiskMonitor([("root", "/"), ])
        #self._monitors["cpu"] = CpuMonitor()
        self._monitors["memory"] = MemoryMonitor()
        for monitor in self._monitors.values():
            for sensor in monitor.sensors():
                self.add_sensor(sensor)

    def start(self):
        log.debug("Starting server")
        super(UniversalBackendNode, self).start()
        for name, monitor in self._monitors.items():
            log.debug(
                "Starting {0} monitor with 1 second polling".format(name))
            monitor.start(1000, self.ioloop)

    def stop(self):
        for name, monitor in self._monitors.items():
            log.debug("Stopping {0} monitor".format(name))
            monitor.stop()
        log.debug("Stopping server")
        return super(UniversalBackendNode, self).stop()
        # deregister self with master

    def _create_pipeline_server(self, name, pipeline_name):
        if name in self._pipeline_servers:
            raise PipelineNameExists(name)
        if pipeline_name not in PIPELINE_REGISTRY:
            raise InvalidPipeline("Invalid pipeline name "+pipeline_name)
        pipeline_type = PIPELINE_REGISTRY[pipeline_name]["class"]
        server = PipelineServer(self.bind_address[0], 0, pipeline_type)
        self._pipeline_servers[name] = server
        server.start()
        return server

    def _create_pipeline_client(self, name, server):
        if name in self._pipeline_clients:
            raise ClientExists
        client = KATCPClientResource(dict(
            name=name,
            address=server.bind_address,
            controlled=True))
        client.start()
        self._pipeline_clients[name] = client
        return client

    @request(Str(), Str())
    @return_reply(Str())
    def request_configure(self, req, pipeline_config, sensors):
        """configure"""
        @coroutine
        def configure(conf):
            futures = {}
            for pipeline in conf:
                name = pipeline["name"]
                pipeline_name = pipeline["pipeline_name"]

                try:
                    server = self._create_pipeline_server(name, pipeline_name)
                except Exception as error:
                    log.error(str(error))
                    req.reply("fail", str(error))
                    return
                else:
                    req.inform("Created pipeline server '{0}'".format(name))

                try:
                    client = self._create_pipeline_client(name, server)
                except Exception as error:
                    log.error(str(error))
                    req.reply("fail", str(error))
                    return
                else:
                    req.inform("Created pipeline client '{0}'".format(name))
                yield client.until_synced()
                futures[name] = client.req.configure(
                    pack_dict(pipeline["config"]), sensors)

            for name, future in futures.items():
                configure_response = yield future
                if configure_response.reply.reply_ok():
                    req.inform("Pipeline '{0}' configured".format(name))
                else:
                    reply = ("Configuration of pipeline '{0}' "
                             "failed with message: {1}").format(
                        name, str(configure_response.messages))
                    log.error(reply)
                    req.reply("fail", reply)
                    return
            req.reply("ok", "All pipelines created and configured")
            self._active.set_value(True)

        if self._active.value():
            msg = ("Node is already active, "
                   "deconfigure before sending new configure commands")
            log.error(msg)
            return ("fail", msg)
        conf = unpack_dict(pipeline_config)
        self.ioloop.add_callback(lambda: configure(conf))
        raise AsyncReply

    @request()
    @return_reply(Str())
    def request_deconfigure(self, req):
        """deconf"""
        @coroutine
        def deconfigure():
            futures = {}
            for name, client in self._pipeline_clients.items():
                futures[name] = client.req.deconfigure()
            for name, client in self._pipeline_clients.items():
                response = yield futures[name]
                if not response.reply.reply_ok():
                    req.inform(
                        "Warning: failure on deconfigure of '{0}': {1}".format(
                            name, str(
                                response.messages)))
            for name, server in self._pipeline_servers.items():
                yield server.stop()
            for name, client in self._pipeline_clients.items():
                client.stop()
            self._pipeline_clients = {}
            self._pipeline_servers = {}
            req.reply("ok", "Deconfigured node")
            self._active.set_value(False)
        self.ioloop.add_callback(deconfigure)
        raise AsyncReply

    @coroutine
    def _send_to_all(self, cmd, req, *args, **kwargs):
        futures = {}
        for name, client in self._pipeline_clients.items():
            futures[name] = client.req[cmd](*args, **kwargs)
        for name, future in futures.items():
            response = yield future
            if response.reply.reply_ok():
                req.inform(
                    "Pipeline '{0}' '{1}' command success".format(
                        name, cmd))
            else:
                req.inform(
                    "Pipeline '{0}' '{1}' command failure [error: {2}]".format(
                        name, cmd, str(
                            response.reply)))
        req.reply("ok", "{0} command passed to all pipelines".format(cmd))

    @request(Str())
    @return_reply(Str())
    def request_start(self, req, sensors):
        """start"""
        self.ioloop.add_callback(
            lambda: self._send_to_all(
                "start", req, sensors))
        raise AsyncReply

    @request()
    @return_reply(Str())
    def request_stop(self, req):
        """stop"""
        self.ioloop.add_callback(lambda: self._send_to_all("stop", req))
        raise AsyncReply

    @request()
    @return_reply(Str())
    def request_reset(self, req):
        """reset"""
        self.ioloop.add_callback(lambda: self._send_to_all("reset", req))
        raise AsyncReply

    @request()
    @return_reply(Str())
    def request_pipeline_avail(self, req):
        """Return available pipelines"""
        for name, info in PIPELINE_REGISTRY.items():
            border = "-" * 50
            msg = ("\n" + border + "\n"
                   "Name: {name}\n"
                   "Requires Nvidia support: {requires_nvidia}\n"
                   "Description:\n{description}\n").format(name=name, **info)
            req.inform(msg)
        response = json.dumps(PIPELINE_REGISTRY.keys())
        return ("ok", response)

    @request(Str(), Str())
    @return_reply(Str())
    def request_pipeline_create(self, req, name, pipeline_name):
        """Create a PipelineServer instance"""
        @coroutine
        def create_pipeline_server():
            try:
                server = self._create_pipeline_server(name, pipeline_name)
            except PipelineNameExists:
                req.reply(
                    "fail",
                    "Pipeline already exists with name '{0}'".format(name))
            except InvalidPipeline:
                req.reply(
                    "fail", "No pipeline type named '{0}'".format(
                        pipeline_name))
            except Exception as error:
                req.reply("fail", "Unknown error [{0}]".format(str(error)))
            else:
                addr = server.bind_address
                req.inform("Server started at {0}".format(addr))
                server_str = ":".join([addr[0], str(addr[1])])
                req.reply("ok", server_str)
        self.ioloop.add_callback(create_pipeline_server)
        raise AsyncReply

    @request()
    @return_reply(Int())
    def request_pipeline_list(self, req):
        """List running pipeline servers"""
        msg = "\nName\tAddress\n"
        for name, server in self._pipeline_servers.items():
            msg += "{0}\t{1}\n".format(name, server.bind_address)
        req.inform(msg)
        return ("ok", len(self._pipeline_servers.keys()))

    @request(Str())
    @return_reply(Str())
    def request_pipeline_destroy(self, req, name):
        """Create a PipelineServer instance"""
        if name in self._pipeline_servers.keys():
            server = self._pipeline_servers[name]
            self.ioloop.add_callback(server.stop)
            return ("ok", "ok")
        else:
            return ("fail", "No pipeline named '{0}'".format(name))


    @request()
    @return_reply(Str())
    def request_status(self, req):
        """Return status for UBN server"""
        status = {}
        @coroutine
        def status_query():
            status["sensors"] = {}
            for name, sensor in self._sensors.items():
                status["sensors"][name] = sensor.value()

            futures = {}
            for name, client in self._pipeline_clients.items():
                if not client.is_connected():
                    status[name] = {"status":"offline"}
                    continue
                else:
                    status[name] = {"status":"online"}
                    futures[name] = client.req.status()
            for name, future in futures.items():
                response = yield future
                log.debug(response.messages)
                if response.reply.reply_ok():
                    status[name].update(unpack_dict(response.reply.arguments[1]))
                else:
                    log.error(response.reply)
            req.reply("ok",pack_dict(status))
        self.ioloop.add_callback(status_query)
        raise AsyncReply
