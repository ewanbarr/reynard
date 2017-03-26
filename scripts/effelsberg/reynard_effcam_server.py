#!/usr/bin/env python
import signal
import tornado
import logging
import json
from optparse import OptionParser
from reynard.effelsberg.servers import EffCAMServer

log = logging.getLogger("reynard.effcam_server")

@tornado.gen.coroutine
def on_shutdown(ioloop, server):
    log.info("Shutting down server")
    yield server.stop()
    ioloop.stop()

def parse_backend(x):
    name,ip,port = x.split(":")
    return name,ip,int(port)

if __name__ == "__main__":
    usage = "usage: %prog [options]"
    parser = OptionParser(usage=usage)
    parser.add_option('-p', '--port', dest='port', type=long,
        help='Port number to bind to')
    parser.add_option('', '--status_ip',dest='ssip',type=str,
        help='IP address of status server instance')
    parser.add_option('', '--status_port',dest='ssp',type=long,
        help='Port number of status server instance')
    parser.add_option("-b", "--backend", dest='backend', action="append", type=str,
        help='Address of backend server in form name:ip:port (can be specified multiple times)')
    parser.add_option('', '--log_level',dest='log_level',type=str,
        help='Port number of status server instance',default="INFO")
    (opts, args) = parser.parse_args()

    if not opts.port:
        print "MissingArgument: Port number"
        sys.exit(-1)

    backends = []
    if opts.backend is not None:
        for backend in opts.backend:
            backends.append(parse_backend(backend))

    FORMAT = "[ %(levelname)s - %(asctime)s - %(filename)s:%(lineno)s] %(message)s"
    logger = logging.getLogger('reynard')
    logging.basicConfig(format=FORMAT)
    logger.setLevel(opts.log_level.upper())
    log.info("Starting EffCAMServer instance")
    ioloop = tornado.ioloop.IOLoop.current()
    server = EffCAMServer(("localhost",opts.port),(opts.ssip,opts.ssp),backends)
    signal.signal(signal.SIGINT, lambda sig, frame: ioloop.add_callback_from_signal(
        on_shutdown, ioloop, server))
    def start_and_display():
        server.start()
        log.info("Listening at {0}, Ctrl-C to terminate server".format(server.bind_address))
    ioloop.add_callback(start_and_display)
    ioloop.start()
