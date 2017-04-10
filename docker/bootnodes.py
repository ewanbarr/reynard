import os
import sys
import socket
import json

IMAGE = "docker.mpifr-bonn.mpg.de:5000/reynard:latest"

def bootnode(hostname,port=5100):
    ip = socket.gethostbyname(hostname)
    cmd = ("reynard_ubn_server.py --host {ip} "
           "--port {port} --log_level DEBUG").format(
           ip=ip,port=port)
    docker = ("docker run -d -p {port}:{port} "
              "--name ubn-server --net=host "
              "-v /dev/:/host-dev/ -v /tmp/:/tmp/ "
              "-v /var/run/docker.sock:/var/run/docker.sock "
              "{image} {cmd}").format(image=IMAGE, cmd=cmd,
                                      port=port)
    ssh_cmd = "ssh {0} {1}".format(hostname,docker)
    print ssh_cmd
    os.system(ssh_cmd)
    print "-"*50

def restart(hostname):
    ssh_cmd = "ssh {0} docker restart ubn-server".format(hostname)
    print ssh_cmd
    os.system(ssh_cmd)
    print "-"*50

def restart_all(nodes):
    for node in nodes:
      restart(node)

def boot_all(nodes):
    for node in nodes:
      bootnode(node)

if __name__ == "__main__":
    from argparse import ArgumentParser
    usage = "{prog} [options]".format(prog=sys.argv[0])
    parser = ArgumentParser(usage=usage)
    parser.add_argument('-n','--nodes', nargs='+',
        help='Hosts to boot ubn servers on',
        default=None, required=False)
    parser.add_argument('-c','--config', type=str,
        help='Configuration containing nodes to be booted',
        default=None, required=False)
    parser.add_argument('-r','--restart', type=bool,
        help='Restart ubn servers on all nodes',
        default=False, required=False)
    args = parser.parse_args()

    if args.config:
        with open(args.config) as f:
            conf = json.load(f)
            nodes = [node['host'] for node in conf]
    elif args.nodes:
        nodes = args.nodes
    else:
        print "Must specify a config file or a list of nodes"
        sys.exit()
    if args.restart:
        restart_all(nodes)
    else:
        boot_all(nodes)

