import logging
import sys
import traceback
import katcp
import readline
from optparse import OptionParser
from cmd2 import Cmd
from reynard.utils import StreamClient

logging.basicConfig(level=logging.INFO,
                    stream=sys.stderr,
                    format="%(asctime)s - %(name)s - %(filename)s:"
                    "%(lineno)s - %(levelname)s - %(message)s")

log = logging.getLogger("reynard.basic_cli")


class KatcpCli(Cmd):
    """
    @brief      Basic command line interface to KATCP device

    @detail     This class provides a command line interface to
                to any katcp.DeviceClient subclass. Behaviour of the
                interface is determined by the client object passed
                at instantiation.
    """
    Cmd.shortcuts.update({'?': 'katcp'})
    def __init__(self,client,*args,**kwargs):
        """
        @brief  Instantiate new KatcpCli instance

        @params client A DeviceClient instance
        """
        self.client = client
        Cmd.__init__(self,args,kwargs)

    def do_katcp(self, arg, opts=None):
        """
        @brief      Send a request message to a katcp server

        @param      arg   The request
        """
        request = "?" + "".join(arg)
        log.info("Request: %s"%request)
        try:
            msg = katcp_parser.parse(request)
            client.ioloop.add_callback(client.send_message, msg)
        except Exception, e:
            e_type, e_value, trace = sys.exc_info()
            reason = "\n".join(traceback.format_exception(
                e_type, e_value, trace, 20))
            log.exception(reason)

if __name__ == "__main__":
    usage = "usage: %prog [options]"
    parser = OptionParser(usage=usage)
    parser.add_option('-a', '--host', dest='host', type="string", default="", metavar='HOST',
                      help='attach to server HOST (default="" - localhost)')
    parser.add_option('-p', '--port', dest='port', type=int, default=1235, metavar='N',
                      help='attach to server port N (default=1235)')
    (opts, args) = parser.parse_args()
    katcp_parser = katcp.MessageParser()
    log.info("Client connecting to port %s:%d, Ctrl-C to terminate." % (opts.host, opts.port))
    client = StreamClient(opts.host, opts.port)
    client.start()
    try:
        app = KatcpCli(client)
        app.prompt = "(katcp CLI %s:%d) " % (opts.host, opts.port)
        app.cmdloop()
    except Exception as error:
        log.exception("Error from CLI")
    finally:
        client.stop()
        client.join()
