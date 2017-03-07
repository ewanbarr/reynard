import signal
import tornado
import logging
from optparse import OptionParser
from reynard.effelsberg.paf.servers import PafInterfaceServer

log = logging.getLogger('reynard.effelsberg.paf_interface_server')

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
    (opts, args) = parser.parse_args()
    log.info("Starting PafInterfaceServer instance listening on port "
        "{opts.port}, Ctrl-C to terminate server".format(opts=opts))
    ioloop = tornado.ioloop.IOLoop.current()
    server = PafInterfaceServer(opts.host, opts.port)
    signal.signal(signal.SIGINT, lambda sig, frame: ioloop.add_callback_from_signal(
        on_shutdown, ioloop, server))
    ioloop.add_callback(server.start)
    ioloop.start()