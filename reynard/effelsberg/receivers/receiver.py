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


class MetaReceiver(type):
    @staticmethod
    def decorator(func,configured_state):
        """Return a wrapped instance method"""
        def wrapper(self, *args, **kwargs):
            return_value = func(self, *args, **kwargs)
            self.configured = configured_state
            return return_value
        return wrapper

    def __new__(cls, name, bases, attrs):
        """If the class has a 'run' method, wrap it"""
        for method,state in [['configure',True],['deconfigure',False]]:
            if method not in attrs:
                attrs[method] = cls.decorator(lambda *args,**kwargs:None,state)
            else:
                attrs[method] = cls.decorator(attrs[method],state)
        if not 'trigger' in attrs:
            attrs['trigger'] = lambda *args,**kwargs:None
        if not 'get_capture_nodes' in attrs:
            attrs['get_capture_nodes'] = lambda *args,**kwargs:[]
        attrs['configured'] = False
        return super(MetaReceiver, cls).__new__(cls, name, bases, attrs)

class Receiver(object):
    __metaclass__ = MetaReceiver




