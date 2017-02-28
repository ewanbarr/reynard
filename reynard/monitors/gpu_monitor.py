import os
import psutil
import logging
from time import sleep
#from reynard.monitors import Monitor
from monitor import Monitor
from subprocess import check_call

log = logging.getLogger("reynard.monitor.gpu")

class CpuMonitor(Monitor):
    def __init__(self,polling_interval=1):
        super(CpuMonitor,self).__init__(polling_interval)
        for ii in range(psutil.cpu_count()):
            self._params["cpu%d"%ii] = {"percent":0, "temp":0}

    def update_values(self):
        percents = psutil.cpu_percent(interval=1,percpu=True)
        for ii,percent in enumerate(percents):
            self._params["cpu%d"%ii]["percent"] = percent
            self._params["cpu%d"%ii]["temp"] = 25.0

if __name__ == "__main__":
    def test(params):
        print params
    volumes = {"root":"/"}
    monitor = CpuMonitor(1)
    monitor.register(test)
    monitor.start()
    sleep(10)
    monitor.stop()