import logging
import tempfile
from docker.errors import APIError
from reynard.pipelines import Pipeline, reynard_pipeline
from reynard.dada import render_dada_header, make_dada_key_string

log = logging.getLogger("reynard.PafFrbPipeline")

#
# NOTE: For this to run properly the host /tmp/
# directory should be mounted onto the launching container.
# This is needed as docker doesn't currently support
# container to container file copies.
#

DESCRIPTION = """
This pipeline captures data from the PAF beamformer, performing
channelisation, filterbank generation and ultimately a fast
transient search.
""".lstrip()


@reynard_pipeline("PafFrbPipeline",
                  description=DESCRIPTION,
                  version="1.0",
                  requires_nvidia=True
                  )
class PafFrbPipeline(Pipeline):
    def __init__(self):
        super(PafFrbPipeline, self).__init__()
        self._volumes = ["/tmp/:/tmp/"]
        self._dada_key = None
        self._config = None

    def _configure(self, config, sensors):
        self._config = config
        self._volumes.append("{}:/output/".format(config["output_path"]))

    def _start(self, sensors):
        header = self._config["dada_header_params"]
        header["ra"] = sensors["ra"]
        header["dec"] = sensors["dec"]
        source_name = sensors["source-name"]
        try:
            source_name = source_name.split("_")[0]
        except BaseException:
            pass
        header["source_name"] = source_name
        header["obs_id"] = "{0}_{1}".format(
            sensors["scannum"], sensors["subscannum"])

        dada_header_file = tempfile.NamedTemporaryFile(
            mode="w",
            prefix="reynard_dada_header_",
            suffix=".txt",
            dir="/tmp/",
            delete=False)
        log.debug(
            "Writing dada header file to {0}".format(
                dada_header_file.name))
        header_string = render_dada_header(header)
        dada_header_file.write(header_string)
        log.debug("Header file contains:\n{0}".format(header_string))
        dada_key_file = tempfile.NamedTemporaryFile(
            mode="w",
            prefix="reynard_dada_keyfile_",
            suffix=".key",
            dir="/tmp",
            delete=False)
        log.debug("Writing dada key file to {0}".format(dada_key_file.name))
        key_string = make_dada_key_string(self._dada_key)
        dada_key_file.write(make_dada_key_string(self._dada_key))
        log.debug("Dada key file contains:\n{0}".format(key_string))
        dada_header_file.close()
        dada_key_file.close()

        self._set_watchdog("dspsr", callback=self.stop)
        self._set_watchdog("udp2db")
        self._set_watchdog("dbmonitor", persistent=True)

        ulimits = [{
            "Name": "memlock",
            "Hard": -1,
            "Soft": -1
        }]

        cmd = "dspsr {args} -N {source_name} {keyfile}".format(
            args=self._config["dspsr_params"]["args"],
            source_name=source_name,
            keyfile=dada_key_file.name)
        log.debug("Running command: {0}".format(cmd))
        self._docker.run(self._config["dspsr_params"]["image"], cmd,
                         detach=True, name="dspsr", ipc_mode="host",
                         volumes=self._volumes, ulimits=ulimits,
                         requires_nvidia=True)

        cmd = ("LD_PRELOAD=libvma.so udp2db "
               "-k {key} {args} -H {headerfile}").format(
            key=self._dada_key,
            args=self._config["udp2db_params"]["args"],
            headerfile=dada_header_file.name)
        log.debug("Running command: {0}".format(cmd))
        self._docker.run(
            self._config["udp2db_params"]["image"],
            cmd,
            detach=True,
            volumes=self._volumes,
            name="udp2db",
            ipc_mode="host",
            network_mode="host",
            requires_vma=True,
            ulimits=ulimits)

        cmd = "dada_dbmonitor -k {key} {args}".format(
            key=self._dada_key,
            args=self._config["dada_dbmonitor_params"]["args"])
        log.debug("Running command: {0}".format(cmd))
        self._docker.run(self._config["dada_dbmonitor_params"]["image"], cmd,
                         detach=True, name="dbmonitor", ipc_mode="host")

    def _stop(self):
        for name in ["dspsr", "udp2db", "dbmonitor"]:
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
        cmd = "dada_db -d -k {0}".format(self._dada_key)
        log.debug("Running command: {0}".format(cmd))
        self._docker.run("psr-capture", cmd, remove=True, ipc_mode="host")

    def _status(self):
        reply = {}
        reply["state"] = self.state
        if self.state == "running":
            container_info = []
            for name in ["dspsr", "udp2db", "dbmonitor"]:
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
