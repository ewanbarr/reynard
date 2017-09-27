import sys
from tempfile import NamedTemporaryFile
from subprocess import Popen
from katcp import DeviceClient
from reynard.utils.katcp import decode_katcp_message

class XTermStream(object):
    def __init__(self):
        self.tempfile = NamedTemporaryFile(mode="w")
        self.xterm = Popen(["xterm", "-e", "tail", "-f", self.tempfile.name])

    def write(self, msg):
        self.tempfile.file.write(msg)
        self.tempfile.file.flush()

    def close(self):
        self.xterm.terminate()
        self.tempfile.close()


class StreamClient(DeviceClient):
    """
    @brief A basic KATCP client that sends replies to a stream

    """
    def __init__(self, server_host, server_port, stream=sys.stdout):
        self.stream = stream
        super(StreamClient, self).__init__(server_host, server_port)

    def _to_stream(self, prefix, msg):
        self.stream.write("%s:\n%s\n" %
                          (prefix, decode_katcp_message(msg.__str__())))

    def unhandled_reply(self, msg):
        """Deal with unhandled replies"""
        self._to_stream("Unhandled reply", msg)

    def unhandled_inform(self, msg):
        """Deal with unhandled informs"""
        self._to_stream("Unhandled inform", msg)

    def unhandled_request(self, msg):
        """Deal with unhandled requests"""
        self._to_stream("Unhandled request", msg)