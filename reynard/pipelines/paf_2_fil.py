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
        self._volumes = ["/tmp/:/scratch/"]
        self._dada_key = None
        self._config = None

    def _configure(self, config, sensors):
        self._config = config
        self._volumes.append("{}:/output/".format(config["output_path"]))

    def _start(self, sensors):
        paf_config_file = tempfile.NamedTemporaryFile(
            mode="w",
            prefix="reynard_paf_config_",
            suffix=".txt",
            dir="/scratch/",
            delete=False)
        log.debug(
            "Writing paf config file to {0}".format(
                paf_config_file.name))
        for line in self._config["config_file_params"]:
            paf_config_file.write(line+"\n")
        paf_config_file.close()

        self._set_watchdog("paf", persistent=True)

        ulimits = [{
            "Name": "memlock",
            "Hard": -1,
            "Soft": -1
        }]

        cmd = "pafrb --config {config} -o /output/ -v".format(
            config=paf_config_file.name)
        log.debug("Running command: {0}".format(cmd))
        self._docker.run(self._config["image"], cmd,
                         detach=True, name="paf",
                         volumes=self._volumes,
                         network_mode="host",
                         ulimits=ulimits,
                         requires_nvidia=True)

    def _stop(self):
        for name in ["paf"]:
            container = self._docker.get(name)
            try:
                log.debug(
                    "Stopping {name} container".format(
                        name=container.name))
                container.stop()
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

    def _status(self):
        reply = {}
        reply["state"] = self.state
        if self.state == "running":
            container_info = []
            for name in ["paf"]:
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
