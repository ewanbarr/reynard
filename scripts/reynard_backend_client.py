import sys
import tornado
import logging
from argparse import ArgumentParser
from katcp.resource_client import KATCPClientResource

log = logging.getLogger('reynard.effelsberg.effcam_client')

def client_request(func):
    def wrapped(client, *args, **kwargs):
        yield client.until_synced()
        response = yield func(client,*args,**kwargs)
        if not response.reply.reply_ok():
            log.warning(str(response))
        else:
            log.info(str(response))
        ioloop.stop()
    return wrapped

@tornado.gen.coroutine
@client_request
def arm(client):
    log.info("Arming PAF backend")
    return client.req.arm()

@tornado.gen.coroutine
@client_request
def disarm(client):
    log.info("Disarming PAF backend")
    return client.req.disarm()

@tornado.gen.coroutine
@client_request
def configure(client, config):
    log.info("Configuring PAF backend with file: {conf}".format(conf=config))
    return client.req.configure(config)

if __name__ == "__main__":
    usage = "usage: {prog} [options]".format(prog=sys.argv[0])
    parser = ArgumentParser(usage=usage)
    required = parser.add_argument_group('required arguments')
    required.add_argument('-H','--host', dest='host', type=str, metavar='IP',
                      help='IP address of PAF interface server')
    required.add_argument('-p', '--port', dest='port', type=long, metavar='N',
                      help='listening port for PAF interface server')
    exclusive = parser.add_argument_group('mutually exclusive arguments')
    group = exclusive.add_mutually_exclusive_group()
    group.add_argument('-c', '--configure', dest='configure', type=str, default="", metavar='CONFIG_FILE',
                      help='configure PAF with CONFIG_FILE')
    group.add_argument('-a', '--arm', dest='arm', action='store_true',
                      help='arm the PAF backend')
    group.add_argument('-d', '--disarm', dest='disarm', action='store_true',
                      help='disarm the PAF backend')
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)

    ioloop = tornado.ioloop.IOLoop.current()
    client = KATCPClientResource(dict(
        name="web-interface-client",
        address=(args.host, args.port),
        controlled=True))
    ioloop.add_callback(client.start)
    if args.configure:
        ioloop.add_callback(lambda: configure(client,args.configure))
    elif args.arm:
        ioloop.add_callback(lambda: arm(client))
    elif args.disarm:
        ioloop.add_callback(lambda: disarm(client))
    else:
        raise Exception("No command given")
        ioloop.add_callback(ioloop.stop)
    ioloop.start()