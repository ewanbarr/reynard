import os

class InvalidConfiguration(Exception):
    pass

def get_config_dir():
    try:
        return os.environ["REYNARD_CONFIG"]
    except KeyError as error:
        raise Exception("No REYNARD_CONFIG environment variable set")

def get_default_config(receiver,tag):
    fname = os.path.join(get_config_dir(),"defaults",receiver,tag+".json")
    if os.path.isfile(fname):
        with open(fname,"r") as f:
            return f.read()
    else:
        raise InvalidConfiguration("No configuration found [{0}/{1}.json]".format(receiver,tag))

def get_config(project,receiver,tag):
    fname = os.path.join(get_config_dir(),project,receiver,tag+".json")
    if os.path.isfile(fname):
        with open(fname,"r") as f:
            return f.read()
    else:
        return get_default_config(receiver,tag)