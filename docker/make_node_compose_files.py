import os
import sys
import tempfile
import json
import jinja2

TEMPLATE_FILE = "docker-compose-node.template"

def make_compose_file(host,port=5100,logging_address="pacifix0:5514"):
    with open(TEMPLATE_FILE,"r") as template_file:
        template = template_file.read()
    rendered = jinja2.Template(template).render(
        host=host, port=port, logging_address=logging_address)
    out_dir = "/home/share/reynard/{}".format(host)
    try:
        os.makedirs(out_dir)
    except:
        pass
    out_file = os.path.join(out_dir,"docker-compose.yml")
    with open(out_file,"w") as out:
        out.write(rendered)

if __name__ == "__main__":
    from argparse import ArgumentParser
    usage = "{prog} [options]".format(prog=sys.argv[0])
    parser = ArgumentParser(usage=usage)
    parser.add_argument('-n','--nodes', nargs='+',
        help='Hosts to create compose files for ',
        default=None, required=False)
    parser.add_argument('-c','--config', type=str,
        help='Configuration containing hosts to generate compose files for',
        default=None, required=False)
    parser.add_argument('-l','--logging_address', type=str,
        help='Address of rsyslog logger',
        default="pacifix0:5514", required=False)
    args = parser.parse_args()
    if args.config:
        with open(args.config) as f:
            conf = json.load(f)
            nodes = [node['host'] for node in conf]
    else:
        nodes = args.nodes

    for node in nodes:
        make_compose_file(node,port=5100,logging_address=args.logging_address)

