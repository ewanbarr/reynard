import logging
import json
import tempfile
from docker.errors import APIError
from reynard.pipelines import Pipeline, reynard_pipeline
from reynard.dada import render_dada_header, make_dada_key_string

log = logging.getLogger("reynard.TestPipeline")

#
# NOTE: For this to run properly the host /tmp/
# directory should be mounted onto the launching container.
# This is needed as docker doesn't currently
# support container to container file copies.
#

DESCRIPTION = """
This pipeline creates a dada data buffer and with a single writer
and single consumer.
The pipeline does nothing useful and is intended only for test purposes.
""".lstrip()


@reynard_pipeline("TestPipeline",
                  description=DESCRIPTION,
                  version="1.0",
                  requires_nvidia=False
                  )
class Junk2Db2Null(Pipeline):
    def __init__(self):
        super(Junk2Db2Null, self).__init__()
        self._volumes = ["/tmp/:/tmp/"]
        self._dada_key = None
        self._duration = None
        self._config = None

    def _configure(self, config, sensors):
        self._config = config
        self._dada_key = config["key"]
        self._duration = config["runtime"]
        try:
            self._deconfigure()
        except Exception as error:
            log.warning(str(error))
        log.debug("Creating dada buffer [key: {0}]".format(self._dada_key))
        self._docker.run("psr-capture",
                         "dada_db -k {0} -n 8 -b 16000000".format(
                             self._dada_key),
                         remove=True,
                         ipc_mode="host")

    def _start(self, sensors):
        header = self._config["dada_header_params"]
        header["ra"] = sensors["ra"]
        header["dec"] = sensors["dec"]
        header["source_name"] = sensors["source-name"]
        header["obs_id"] = "{0}_{1}".format(
            sensors["scannum"], sensors["subscannum"])
        dada_header_file = tempfile.NamedTemporaryFile(
            mode="w", prefix="reynard_dada_header_", dir="/tmp/", delete=False)
        dada_key_file = tempfile.NamedTemporaryFile(
            mode="w", prefix="reynard_dada_keyfile_", dir="/tmp", delete=False)
        dada_header_file.write(render_dada_header(header))
        dada_key_file.write(make_dada_key_string(self._dada_key))
        dada_header_file.close()
        dada_key_file.close()
        self._set_watchdog("dbnull", persistent=True)
        self._set_watchdog("junkdb", callback=self.stop)
        self._set_watchdog("dbmonitor", persistent=True)

        # The start up time can be improved here by pre-createing these
        # containers
        self._docker.run(
            "psr-capture", "dada_dbnull -k {0}".format(self._dada_key),
            detach=True, name="dbnull", ipc_mode="host")
        self._docker.run("psr-capture",
                         "dada_junkdb -k {0} -r 64 -t {1} -g {2}".format(
                             self._dada_key,
                             self._duration,
                             dada_header_file.name),
                         detach=True,
                         volumes=self._volumes,
                         name="junkdb",
                         ipc_mode="host")
        self._docker.run(
            "psr-capture", "dada_dbmonitor -k {0}".format(self._dada_key),
            detach=True, name="dbmonitor", ipc_mode="host")

        # For observations that require firware triggers
        # the loop that waits for the UDPDB trigger should go here

    def _stop(self):
        for name in ["dbnull", "junkdb", "dbmonitor"]:
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
            except BaseException:
                pass

    def _deconfigure(self):
        log.debug("Destroying dada buffer")
        self._docker.run(
            "psr-capture", "dada_db -d -k {0}".format(self._dada_key),
            remove=True, ipc_mode="host")

    def _status(self):
        reply = {}
        reply["state"] = self.state
        if self.state == "running":
            container_info = []
            for name in ["dbnull", "junkdb", "dbmonitor"]:
                container = self._docker.get(name)
                detail = {
                    "name": container.name,
                    "status": container.status,
                    "procs": container.top(),
                    "logs": container.logs(tail=20)
                }
                container_info.append(detail)
            reply["info"] = container_info
        return reply
