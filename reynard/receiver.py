RECEIVER_REGISTRIES = {}

class InvalidReceiver(Exception):
    pass

def reynard_receiver(telescope,receiver):
    telescope = telescope.lower()
    receiver = receiver.lower()
    def wrapped(cls):
        if not RECEIVER_REGISTRIES.has_key(telescope):
            RECEIVER_REGISTRIES[telescope] = {}
        RECEIVER_REGISTRIES[telescope][receiver] = cls
        return cls
    return wrapped

def get_receiver(telescope,receiver):
    telescope = telescope.lower()
    receiver = receiver.lower()
    try:
        return RECEIVER_REGISTRIES[telescope][receiver]
    except KeyError as error:
        raise InvalidReceiver("No receiver called '{0}' for telescope '{1}'".format(receiver,telescope))


