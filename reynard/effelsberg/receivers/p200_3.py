import logging
import docker
from .receiver import reynard_receiver, Receiver
from reynard.effelsberg.config import get_node_by_ethernet_interface

log = logging.getLogger("reynard.effelsberg.receivers.p200-3")

@reynard_receiver("effelsberg", "P200-3")
class P200Mode3(Receiver):
    def __init__(self):
        self.client = docker.from_env()
        super(P200Mode3,self).__init__()

    def get_capture_nodes(self):
        """
        @brief      Gets the capture nodes.

        @param      self  The object

        @return     The capture nodes.
        """
        # this should also return something to do with ports
        return [get_node_by_ethernet_interface("effelsberg","10.0.5.100")]

    def _run(self, cmd):
        log.debug("Calling: {}".format(cmd))
        self.client.containers.run(
            "docker.mpifr-bonn.mpg.de:5000/firmware-control:latest",
            cmd,
            network_mode="host",
            remove=True)
        log.debug("Completed: {}".format(cmd))

    def configure(self):
        log.info("Configuring firmware for P200-3")
        cmd = "python full_res_dual_mode.py 134.104.75.134 --noprogram --enable"
        self._run(cmd)

    def trigger(self):
        log.info("Triggering firmware for P200-3")
        cmd = "python full_res_dual_mode.py 134.104.75.134 --noprogram --trigger"
        self._run(cmd)

    def deconfigure(self):
        log.info("Deconfiguring firmware for P200-3")
        cmd = "python full_res_dual_mode.py 134.104.75.134 --noprogram --disable"
        self._run(cmd)


