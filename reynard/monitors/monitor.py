import logging
from tornado.ioloop import PeriodicCallback, IOLoop


log = logging.getLogger("reynard.monitor")


class Monitor(object):
    def __init__(self):
        self._monitor = None
        self._sensors = {}

    def start(self, poll=1000, ioloop=None):
        self._monitor = PeriodicCallback(
            self.update_values, poll, io_loop=ioloop)
        self._monitor.start()

    def stop(self):
        if self._monitor is not None:
            self._monitor.stop()

    def sensors(self):
        return self._sensors.values()

    def update_values(self):
        raise NotImplementedError


def monitor_test(monitor):
    ioloop = IOLoop()
    monitor.start(1000, ioloop)
    ioloop.call_later(5, ioloop.stop)
    ioloop.start()
    monitor.stop()
