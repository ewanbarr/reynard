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

if __name__ == "__main__":

    FORMAT = "[ %(levelname)s - %(asctime)s - %(filename)s:%(lineno)s] %(message)s"
    logger = logging.getLogger('reynard')
    logging.basicConfig(format=FORMAT)
    logger.setLevel(logging.DEBUG)

    usage = "usage: %prog [options]"
    parser = OptionParser(usage=usage)
    parser.add_option('-p', '--port', dest='port', type=long,
        help='Port number to bind to')
    parser.add_option('', '--status_ip',dest='ssip',type=str,
        help='IP address of status server instance')
    parser.add_option('', '--status_port',dest='ssp',type=long,
        help='Port number of status server instance')

    (opts, args) = parser.parse_args()
    log.info("Starting EffCAMServer instance")
    ioloop = tornado.ioloop.IOLoop.current()
    config = json.load(config_file)
    server = EffCAMServer(("localhost",opts.port),(opts.ssip,opts.ssp))
    signal.signal(signal.SIGINT, lambda sig, frame: ioloop.add_callback_from_signal(
        on_shutdown, ioloop, server))
    def start_and_display():
        server.start()
        print "Listening at {0}, Ctrl-C to terminate server".format(server.bind_address)
    ioloop.add_callback(start_and_display)
    ioloop.start()
