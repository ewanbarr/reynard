import os
import logging
from reynard.monitors import Monitor
from katcp import Sensor

log = logging.getLogger("reynard.monitor.disk")


class DiskMonitor(Monitor):
    def __init__(self, volumes):
        super(DiskMonitor, self).__init__()
        self._volumes = volumes
        for name, path in self._volumes:
            name_ = "%s_partition_size" % name
            self._sensors[name_] = Sensor.float(
                name_, description="total size of %s partition" %
                name, params=[
                    8192, 1e9], unit="GB", default=0)
            name_ = "%s_partition_avail" % name
            self._sensors[name_] = Sensor.float(
                name_, description="available space on %s partition" %
                name, params=[
                    8192, 1e9], unit="GB", default=0)

    def update_values(self):
        for name, path in self._volumes:
            statvfs = os.statvfs(path)
            size = statvfs.f_frsize * statvfs.f_blocks / 1e9
            avail = statvfs.f_frsize * statvfs.f_bavail / 1e9
            percent = 100.0 * avail / size
            if percent < 0.5:
                status = Sensor.ERROR
            if percent < 5:
                status = Sensor.WARN
            else:
                status = Sensor.NOMINAL
            self._sensors["%s_partition_size" % name].set_value(size)
            self._sensors["%s_partition_avail" % name].set_value(avail, status)


if __name__ == "__main__":
    from reynard.monitors.monitor import monitor_test
    FORMAT = "[ %(levelname)s - %(asctime)s - %(filename)s:%(lineno)s] %(message)s"
    logger = logging.getLogger('reynard')
    logging.basicConfig(format=FORMAT)
    logger.setLevel(logging.DEBUG)
    monitor_test(DiskMonitor([("root", "/"), ]))
