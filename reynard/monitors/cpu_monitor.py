import os
import psutil
import logging
from katcp import Sensor
from reynard.monitors import Monitor

log = logging.getLogger("reynard.monitor.cpu")

class CpuMonitor(Monitor):
    def __init__(self):
        super(CpuMonitor,self).__init__()
        for cpu_idx in range(psutil.cpu_count()):
            self._sensors["cpu%02d_percent"%cpu_idx] = Sensor.float("cpu%02d_percent"%cpu_idx,
                description = "percentage usage of cpu%02d"%cpu_idx,
                params = [0,200],
                unit = "%",
                default = 0)
            self._sensors["cpu%02d_temperature"%cpu_idx] = Sensor.float("cpu%02d_temperature"%cpu_idx,
                description = "temperature of cpu%02d"%cpu_idx,
                params = [0,200],
                unit = "Celsius",
                default = 0)

    def update_values(self):
        percents = psutil.cpu_percent(percpu=True)
        for cpu_idx,percent in enumerate(percents):
            self._sensors["cpu%02d_percent"%cpu_idx].set_value(percent)
            self._sensors["cpu%02d_temperature"%cpu_idx].set_value(25.0)

if __name__ == "__main__":
    from reynard.monitors.monitor import monitor_test
    FORMAT = "[ %(levelname)s - %(asctime)s - %(filename)s:%(lineno)s] %(message)s"
    logger = logging.getLogger('reynard')
    logging.basicConfig(format=FORMAT)
    logger.setLevel(logging.DEBUG)
    test_monitor(CpuMonitor())