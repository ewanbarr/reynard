import Queue
import signal
import tornado
import logging
from optparse import OptionParser
from reynard.servers import NodeServer,ManagementNode

log = logging.getLogger('reynard.basic_server')

class Config(object):
    VOLUMES = [("root","/"),]
    NODES = [("localhost",1235),]

@tornado.gen.coroutine
def on_shutdown(ioloop, server):
    log.info("Shutting down server")
    yield server.stop()
    ioloop.stop()

if __name__ == "__main__":
    usage = "usage: %prog [options]"
    parser = OptionParser(usage=usage)
    parser.add_option('-a', '--host', dest='host', type="string", default="", metavar='HOST',
                      help='listen to HOST (default="" - all hosts)')
    parser.add_option('-p', '--port', dest='port', type=long, default=1235, metavar='N',
                      help='attach to port N (default=1235)')
    parser.add_option('-s', '--server_type', dest='server_type', type=str, default="NodeServer",
                      help='server type to start')
    (opts, args) = parser.parse_args()
    log.info("Starting {opts.server_type} instance listening on port "
        "{opts.port}, Ctrl-C to terminate server".format(**locals()))
    ioloop = tornado.ioloop.IOLoop.current()
    if opts.server_type == "NodeServer":
        server = NodeServer(opts.host, opts.port, Config())
    elif opts.server_type == "ManagementNode":
        server = ManagementNode(opts.host, opts.port, Config())
    signal.signal(signal.SIGINT, lambda sig, frame: ioloop.add_callback_from_signal(
        on_shutdown, ioloop, server))
    ioloop.add_callback(server.start)
    ioloop.start()