import os
import logging
from time import sleep
from reynard.monitors import Monitor
from katcp import Sensor

log = logging.getLogger("reynard.monitor.disk")

class DiskMonitor(Monitor):
    def __init__(self,volumes,polling_interval=1):
        super(DiskMonitor,self).__init__(polling_interval)
        self._volumes = volumes
        for name,path in self._volumes:
            name_ = "%s_partition_size"%name
            self._sensors[name_] = Sensor.float(name_,
                description = "total size of %s partition"%name,
                params = [8192,1e9],
                unit = "MB",
                default = 0)
            name_ = "%s_partition_avail"%name
            self._sensors[name_] = Sensor.float(name_,
                description = "available space on %s partition"%name,
                params = [8192,1e9],
                unit = "MB",
                default = 0)

    def update_values(self):
        for name,path in self._volumes:
            statvfs = os.statvfs(path)
            size = statvfs.f_frsize * statvfs.f_blocks
            avail = statvfs.f_frsize * statvfs.f_bavail
            percent = 100.0 * avail/size
            if percent < 0.5:
                status = Sensor.ERROR
            if percent < 5:
                status = Sensor.WARN
            else:
                status = Sensor.NOMINAL
            self._sensors["%s_partition_size"%name].set_value(size)
            self._sensors["%s_partition_avail"%name].set_value(avail,status)


if __name__ == "__main__":
    from reynard.monitors.monitor import monitor_test
    monitor_test(DiskMonitor([("root","/"),]))
