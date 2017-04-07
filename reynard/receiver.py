RECEIVER_REGISTRIES = {}


class InvalidReceiver(Exception):
    pass


def reynard_receiver(telescope, receiver):
    telescope = telescope.lower()
    receiver = receiver.lower()

    def wrapped(cls):
        if telescope not in RECEIVER_REGISTRIES:
            RECEIVER_REGISTRIES[telescope] = {}
        RECEIVER_REGISTRIES[telescope][receiver] = cls
        cls.telescope = telescope
        cls.name = receiver
        return cls
    return wrapped


def get_receiver(telescope, receiver):
    telescope = telescope.lower()
    receiver = receiver.lower()
    try:
        return RECEIVER_REGISTRIES[telescope][receiver]
    except KeyError as error:
        raise InvalidReceiver(
            "No receiver called '{0}' for telescope '{1}'".format(
                receiver, telescope))
