#!/usr/bin/env python
import signal
import tornado
import logging
import json
import pkg_resources
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
    parser.add_option('-c', '--config', dest='config', type=str,
                      help='Config file')
    (opts, args) = parser.parse_args()
    log.info("Starting EffCAMServer instance".format(opts=opts))
    ioloop = tornado.ioloop.IOLoop.current()
    config_file = pkg_resources.resource_filename("reynard","config/{0}".format(opts.config))
    config = json.load(config_file)
    server = EffCAMServer(config)
    signal.signal(signal.SIGINT, lambda sig, frame: ioloop.add_callback_from_signal(
        on_shutdown, ioloop, server))
    def start_and_display():
        server.start()
        print "Listening at {0}, Ctrl-C to terminate server".format(server.bind_address)
    ioloop.add_callback(start_and_display)
    ioloop.start()
