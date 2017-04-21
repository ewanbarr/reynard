import logging
import tempfile
import os
from datetime import datetime
from docker.errors import APIError
from reynard.pipelines import Pipeline, reynard_pipeline
from reynard.dada import render_dada_header, make_dada_key_string

log = logging.getLogger("reynard.DspsrMonitor")


class DspsrMonitorThread(Thread):
    def __init__(self, psrchive, path_map):
        Thread.__init__(self)
        self.psrchive = psrchive
        self.path_map = path_map
        self.daemon = True
        self.stop_event = Event()

    def run(self):
        while not self.stop_event():
            for src,dest in self.path_map.items():
                cmd = "rsync {src} {dest}"




DESCRIPTION = """
Monitor a directory for archive files and make plots
""".lstrip()

@reynard_pipeline("DspsrMonitor",
                  description=DESCRIPTION,
                  version="1.0"
                  )
class DspsrMonitor(Pipeline):
    def __init__(self):
        super(DspsrMonitor, self).__init__()
        self._config = None
        self._psrchive = None
        self._path_map = {}

    def _configure(self, config, sensors):
        self._config = config
        workdir = self._config["workdir"]
        if not workdir.startswith("/"):
            raise Exception("Working directory must be an absolute path")
        monitor = self._config["monitor"]
        os.makedirs(workdir)
        for node, src_path in monitor:
            dest_path = os.path.join(workdir,sensors["source-name"],sensors["timestamp"],node)
            os.makedirs(working_path)
            self._path_map["{node}:{src_path}"] = dest_path
        self._set_watchdog("psrchive", persistent=True)
        self._psrchive = self._psrchive = self._docker.run(
            self._config["image"],
            name="psrchive",
            tty=True,
            stdin_open=True,
            detach=True)
        self._psrchive.reload()

    def _start(self, sensors):
        pass


    def _stop(self):
        for name in ["psrchive"]:
            container = self._docker.get(name)
            try:
                log.debug(
                    "Stopping {name} container".format(
                        name=container.name))
                container.kill()
            except APIError:
                pass
            try:
                log.debug(
                    "Removing {name} container".format(
                        name=container.name))
                container.remove()
            except Exception:
                pass

    def _deconfigure(self):
        pass
