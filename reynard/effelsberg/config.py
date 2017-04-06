import os
import json

class InvalidConfiguration(Exception):
    pass

class InterfaceNotFound(Exception):
    pass

def get_config_dir():
    try:
        return os.environ["REYNARD_CONFIG"]
    except KeyError:
        raise Exception("No REYNARD_CONFIG environment variable set")

def get_nodes(node_set):
    fname = os.path.join(get_config_dir(), "nodes",
                         node_set + ".json")
    with open(fname,"r") as f:
        nodes = json.load(f)
    return nodes

def get_node_by_ethernet_interface(node_set, ip):
    nodes = get_nodes(node_set)
    for node in nodes:
        if ip in node["nics"]:
            return node
    else:
        raise InterfaceNotFound(ip)

def get_default_pipeline_config(receiver, tag):
    fname = os.path.join(get_config_dir(), "pipelines",
                         "defaults", receiver, tag + ".json")
    if os.path.isfile(fname):
        with open(fname, "r") as f:
            return f.read()
    else:
        raise InvalidConfiguration(
            "No configuration found [{0}/{1}.json]".format(receiver, tag))

def get_pipeline_config(project, receiver, tag):
    fname = os.path.join(get_config_dir(), "pipelines",
                         project, receiver, tag + ".json")
    if os.path.isfile(fname):
        with open(fname, "r") as f:
            return f.read()
    else:
        return get_default_pipeline_config(receiver, tag)
