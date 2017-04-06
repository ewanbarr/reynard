from collections import namedtuple
from reynard.receiver import reynard_receiver
from reynard.effelsberg.config import get_node_by_ethernet_interface

node = namedtuple("Node", "name ip port")


@reynard_receiver("effelsberg", "P217-3")
class Paf(object):
    def __init__(self):
        pass

    def get_capture_nodes(self):
        """
        @brief      Gets the capture nodes.

        @param      self  The object

        @return     The capture nodes.
        """

        return [get_node_by_ethernet_interface("effelsberg","10.17.0.1")]

    def set_capture_nodes(self):
        pass

    def configure(self):
        pass

    def deconfigure(self):
        pass
