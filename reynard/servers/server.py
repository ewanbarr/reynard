import logging
import sys
import Queue
from katcp import Sensor,DeviceServer,DeviceClient
from katcp.kattypes import request, return_reply, Float, Int, Str
from katcp.resource_client import KATCPClientResource
from katcp.inspecting_client import InspectingClientAsync
from reynard.monitors import DiskMonitor,CpuMonitor,MemoryMonitor

log = logging.getLogger("reynard.server")

class NodeServer(DeviceServer):
    """Basic katcp server providing common sensors.

    """
    VERSION_INFO = ("fbfuse-api",0,1)
    BUILD_INFO = ("fbfuse-implementation",0,1,"rc1")
    DEVICE_STATUSES = ["ok", "degraded", "fail"]

    def __init__(self, server_host, server_port, config):
        self._config = config
        self._monitors = {}
        super(NodeServer,self).__init__(server_host, server_port)

    def setup_sensors(self):
        self._device_status = Sensor.discrete("device-status",
            description = "health status of node",
            params = self.DEVICE_STATUSES,
            default = "ok")
        self.add_sensor(self._device_status)
        self._monitors["disk"] = DiskMonitor(self._config.VOLUMES)
        self._monitors["cpu"] = CpuMonitor()
        self._monitors["memory"] = MemoryMonitor()
        for monitor in self._monitors.values():
            print monitor
            for sensor in monitor.sensors():
                self.add_sensor(sensor)
            monitor.start()

class ManagementNode(NodeServer):
    def __init__(self, server_host, server_port, config, client):
        self._clients = {}
        super(ManagementNode,self).__init__(server_host, server_port, config)

    def setup_sensors(self):
        super(ManagementNode,self).setup_sensors()
        for node,port in self._config.NODES:
            self._clients[node] = KATCPClientResource(dict(
                name='%s-client'%node,
                address=('127.0.0.1', port),
                controlled=True))
            print "prestart"
            print self._clients[node].start()
            #res = IOLoop.current().run_sync(self._clients[node].list_sensors)
            print res
            print "poststart"


class CaptureNode(NodeServer):
    def __init__(self,name,address,port):
        super(CaptureNode,self).__init__(name,address,port)
