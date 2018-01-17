import os
import sys
import socket
import json

def node_cmd(hostname,cmd):
    if cmd == "up":
        cmd = "up -d"
    ssh_cmd = "ssh {0} 'cd /home/share/reynard/{0} && docker-compose {1}'".format(
        hostname,cmd)
    print ssh_cmd
    os.system(ssh_cmd)
    print "-"*50

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
    parser.add_argument('-m','--message', type=str,
        help='Send this message to nodes', required=True)
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
    for node in nodes:
        node_cmd(node,args.message)

