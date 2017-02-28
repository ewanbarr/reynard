import logging
from time import sleep
from threading import Thread, Event

log = logging.getLogger("reynard.monitor")

class Monitor(Thread):
    def __init__(self, polling_interval=1):
        Thread.__init__(self)
        self._polling_interval = polling_interval
        self._stop_event = Event()
        self._sensors = {}
        self.daemon = True

    def run(self):
        while not self._stop_event.is_set():
            self.update_values()
            self._stop_event.wait(self._polling_interval)

    def sensors(self):
        return self._sensors.values()

    def stop(self):
        self._stop_event.set()

    def update_values(self):
        pass

def monitor_test(monitor):
    monitor.start()
    sleep(5)
    for sensor in monitor.sensors():
        print sensor.name,sensor.value()
    sleep(5)
    monitor.stop()

if __name__ == "__main__":
    monitor_test(Monitor())