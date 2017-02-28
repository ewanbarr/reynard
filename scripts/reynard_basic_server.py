import Queue
from optparse import OptionParser
from reynard.servers import NodeServer,ManagementNode


class Config(object):
    VOLUMES = [("root","/"),]
    NODES = [("localhost",1235),]

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

    print "Server listening on port %d, Ctrl-C to terminate server" % opts.port
    restart_queue = Queue.Queue()
    if opts.server_type == "NodeServer":
        server = NodeServer(opts.host, opts.port, Config())
    elif opts.server_type == "ManagementNode":
        server = ManagementNode(opts.host, opts.port, Config())

    server.set_restart_queue(restart_queue)

    server.start()
    print "Started."

    try:
        while True:
            try:
                device = restart_queue.get(timeout=0.5)
            except Queue.Empty:
                device = None
            if device is not None:
                print "Stopping ..."
                device.stop()
                device.join()
                print "Restarting ..."
                device.start()
                print "Started."
    except KeyboardInterrupt:
        print "Shutting down ..."
        server.stop()
        server.join()