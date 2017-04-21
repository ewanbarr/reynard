import logging
import tempfile
import os
import time
import shutil
from datetime import datetime
from docker.errors import APIError
from reynard.pipelines import Pipeline, reynard_pipeline
from reynard.dada import render_dada_header, make_dada_key_string

log = logging.getLogger("reynard.DspsrPipeline")

#
# NOTE: For this to run properly the host /tmp/
# directory should be mounted onto the launching container.
# This is needed as docker doesn't currently support
# container to container file copies.
#

DESCRIPTION = """
This pipeline captures data from the network and passes it to a dada
ring buffer for processing by DSPSR
""".lstrip()

@reynard_pipeline("DspsrPipeline",
                  description=DESCRIPTION,
                  version="1.0",
                  requires_nvidia=True
                  )
class Udp2Db2Dspsr(Pipeline):

    ulimits = [{
        "Name": "memlock",
        "Hard": -1,
        "Soft": -1
    }]

    def __init__(self):
        super(Udp2Db2Dspsr, self).__init__()
        self._volumes = ["/tmp/:/tmp/"]
        self._dada_key = None
        self._config = None

    def _configure(self, config, sensors):
        self._config = config
        self._dada_key = config["dada_db_params"]["key"]
        try:
            self._deconfigure()
        except Exception:
            pass
        cmd = "dada_db -k {key} {args}".format(**config["dada_db_params"])
        log.debug("Running command: {0}".format(cmd))
        self._docker.run(
            self._config["dada_db_params"]["image"],
            cmd, remove=True,
            ipc_mode="host",
            ulimits=self.ulimits)

    def _start(self, sensors):
        header = self._config["dada_header_params"]
        header["ra"] = sensors["ra"]
        header["dec"] = sensors["dec"]
        source_name = sensors["source-name"]
        try:
            source_name = source_name.split("_")[0]
        except Exception:
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
        self._set_watchdog("psrchive")

        ###################
        ## Start up DSPSR
        ###################
        tstr = sensors["timestamp"]
        out_path = os.path.join("/output/",source_name,tstr)
        host_out_path = os.path.join(self._config["base_output_dir"],
            source_name,tstr)
        volumes = ["/tmp/:/tmp/",
                   "{}:/output/".format(
                    self._config["base_output_dir"])]

        # Make output directories via container call
        log.debug("Creating directories")
        log.debug("Running: mkdir -m 664 -p {}".format(out_path))
        self._docker.run(
            self._config["dspsr_params"]["image"],
            "mkdir -m 664 -p {}".format(out_path),
            volumes=volumes,
            remove=True)

        cmd = "dspsr {args} -N {source_name} {keyfile}".format(
            args=self._config["dspsr_params"]["args"],
            source_name=source_name,
            keyfile=dada_key_file.name)
        log.debug("Running command: {0}".format(cmd))
        self._docker.run(
            self._config["dspsr_params"]["image"],
            cmd,
            detach=True,
            name="dspsr",
            ipc_mode="host",
            volumes=volumes,
            working_dir=out_path,
            ulimits=self.ulimits,
            requires_nvidia=True)

        ############################
        ## Start up PSRCHIVE monitor
        ############################

        host_out_dir = os.path.join(self._config["base_monitor_dir"],"/timing/",source_name,tstr)
        out_dir = os.path.join("/output/timing/",source_name,tstr)
        log.debug("Creating directory: {}".format(out_dir))
        self._docker.run(
            self._config["psrchive_params"]["image"],
            "mkdir -m 664 -p {}".format(out_dir),
            volumes=["{}:/output/".format(self._config["base_monitor_dir"])],
            remove=True)

        volumes = [
            "{}:/output/".format(host_out_dir)
            "{}:/input/".format(host_out_path)
            ]

        self._docker.run(
            self._config["psrchive_params"]["image"],
            "exec {}".format(self._config["psrchive_params"]["cmd"]),
            detach=True,
            name="psrchive",
            cpuset_cpus="2",
            volumes=volumes)

        ####################
        ## Start up UDP2DB
        ####################
        cmd = ("LD_PRELOAD=libvma.so taskset -c 1 udp2db "
               "-k {key} {args} -H {headerfile}").format(
            key=self._dada_key,
            args=self._config["udp2db_params"]["args"],
            headerfile=dada_header_file.name)
        cmd = 'bash -c "{cmd}"'.format(cmd=cmd)
        log.debug("Running command: {0}".format(cmd))
        self._docker.run(
            self._config["udp2db_params"]["image"],
            cmd,
            cap_add=["ALL"],
            cpu_shares=262144,
            cpuset_cpus="1",
            detach=True,
            volumes=self._volumes,
            environment={"VMA_MTU":9000},
            name="udp2db",
            ipc_mode="host",
            network_mode="host",
            requires_vma=True,
            ulimits=self.ulimits)

    def _stop(self):
        for name in ["dspsr", "udp2db", "psrchive"]:
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





