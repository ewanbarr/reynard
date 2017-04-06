#!/usr/bin/env python
import signal
import sys
import tornado
import logging
import json
from optparse import OptionParser
from reynard.servers import UniversalBackendNode

log = logging.getLogger("reynard.ubn_server")


@tornado.gen.coroutine
def on_shutdown(ioloop, server):
    log.info("Shutting down server")
    yield server.stop()
    ioloop.stop()


if __name__ == "__main__":
    usage = "usage: %prog [options]"
    parser = OptionParser(usage=usage)
    parser.add_option(
        '-H', '--host', dest='host', type=str,
        help='Hostname to setup on', default="127.0.0.1")
    parser.add_option(
        '-p', '--port', dest='port', type=long,
        help='Port number to bind to')
    parser.add_option(
        '', '--log_level', dest='log_level', type=str,
        help='Port number of status server instance', default="INFO")
    (opts, args) = parser.parse_args()

    if not opts.port:
        print "MissingArgument: Port number"
        sys.exit(-1)

    FORMAT = "[ %(levelname)s - %(asctime)s - %(filename)s:%(lineno)s] %(message)s"
    logger = logging.getLogger('reynard')
    logging.basicConfig(format=FORMAT)
    logger.setLevel(opts.log_level.upper())
    log.info("Starting UniversalBackendNode instance")
    ioloop = tornado.ioloop.IOLoop.current()
    server = UniversalBackendNode(opts.host, opts.port)
    signal.signal(signal.SIGINT,
                  lambda sig, frame: ioloop.add_callback_from_signal(
                      on_shutdown, ioloop, server))

    def start_and_display():
        server.start()
        log.info("Listening at {0}, Ctrl-C to terminate server".format(
            server.bind_address))

    ioloop.add_callback(start_and_display)
    ioloop.start()
