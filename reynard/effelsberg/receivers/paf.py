from reynard.receiver import reynard_receiver, Receiver
from reynard.effelsberg.config import get_node_by_ethernet_interface


@reynard_receiver("effelsberg", "PAF")
class Paf(Receiver):
    def __init__(self):
        pass

    def get_capture_nodes(self):
        """
        @brief      Gets the capture nodes.

        @param      self  The object

        @return     The capture nodes.
        """

        return [get_nodes("effelsberg")]

    def configure(self):
        pass

    def trigger(self):
        pass

    def deconfigure(self):
        pass
