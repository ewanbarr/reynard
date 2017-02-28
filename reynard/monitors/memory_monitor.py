import os
import psutil
import logging
from time import sleep
from reynard.monitors import Monitor
from katcp import Sensor
from subprocess import Popen,PIPE

log = logging.getLogger("reynard.monitor.memory")

class MemoryMonitor(Monitor):
    def __init__(self,polling_interval=1):
        super(MemoryMonitor,self).__init__(polling_interval)
        for node in get_meminfo().keys():
            name_ = "%s_memory_size"%node
            self._sensors[name_] = Sensor.float(name_,
                description = "total memory on %s"%node,
                params = [8192,1e9],
                unit = "MB",
                default = 0)
            name_ = "%s_memory_avail"%node
            self._sensors[name_] = Sensor.float(name_,
                description = "available memory on %s"%node,
                params = [8192,1e9],
                unit = "MB",
                default = 0)

    def update_values(self):
        info = get_meminfo()
        for node in info.keys():
            total = info[node]["MemTotal"]
            avail = info[node]["MemFree"]
            percent = 100.0 * avail/total
            if percent < 5:
                status = Sensor.WARN
            else:
                status = Sensor.NOMINAL
            self._sensors["%s_memory_size"%node].set_value(info[node]["MemTotal"])
            self._sensors["%s_memory_avail"%node].set_value(info[node]["MemFree"],status)

def get_meminfo():
    try:
        return numastat_meminfo()
    except:
        return psutil_meminfo()

def psutil_meminfo():
    tag = "sys"
    out = {tag:{}}
    vmem = psutil.virtual_memory()
    out[tag]["MemTotal"] = vmem.total/1e6
    out[tag]["MemFree"] = vmem.available/1e6
    return out

def numastat_meminfo():
    out = {}
    p = Popen(["numastat","-m"],stdout=PIPE,stderr=PIPE)
    p.wait()
    lines = p.stdout.read().decode().splitlines()
    count = lines[2].count("Node")
    for ii in range(count):
        out["numa%d"%ii] = {}
    for line in lines[4:]:
        split = line.split()
        name = split[0]
        for ii,val in enumerate(split[1:-1]):
            out["numa%d"%ii][name] = float(val)
    return out

if __name__ == "__main__":
    from reynard.monitors.monitor import monitor_test
    monitor_test(MemoryMonitor())

