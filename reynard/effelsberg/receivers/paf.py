from reynard.receiver import reynard_receiver
from reynard.effelsberg.config import get_node_by_ethernet_interface


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

    def configure(self):
        pass

    def trigger(self):
        pass

    def deconfigure(self):
        pass
