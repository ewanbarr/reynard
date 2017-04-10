import socket
import json
import reynard.effelsberg.config as config_manager

IMAGE = "docker.mpifr-bonn.mpg.de:5000/reynard:latest"

def bootnode(hostname,port=5100):
    #ip = socket.gethostbyname(hostname)
    ip = "127.0.0.1"
    cmd = ("reynard_ubn_server.py --host {ip} "
           "--port {port} --log_level DEBUG").format(
           ip=ip,port=port)
    docker = ("docker run -d -p {port}:{port}"
              "--name ubn-server --net=host "
              "-v /dev/:/host-dev/ -v /tmp/:/tmp/ "
              "-v /var/run/docker.sock:/var/run/docker.sock "
              "{image} {cmd}").format(image=IMAGE, cmd=cmd, 
                                      port=port)
    print ("ssh {0} {1}".format(hostname,docker))

def main(nodeset):
    nodes = config_manager.get_nodes(nodeset)
    for node in nodes:
        bootnode(node["host"])

if __name__ == "__main__":
    main("effelsberg")

