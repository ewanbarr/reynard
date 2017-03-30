from collections import namedtuple
from reynard.receiver import reynard_receiver

node = namedtuple("Node","name ip port")

@reynard_receiver("effelsberg","P217-3")
class Paf(object):
    def __init__(self):
        pass

    def get_capture_nodes(self):
        """
        @brief      Gets the capture nodes.

        @param      self  The object

        @return     The capture nodes.
        """

        nodes = []
        nodes.append(node("pacifix0","127.0.0.1",5007))
        return nodes

    def set_capture_nodes(self):
        pass

    def configure(self):
        pass

    def deconfigure(self):
        pass
