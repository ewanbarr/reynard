import logging
import tempfile
import os
import shutil
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from datetime import datetime
from docker.errors import APIError
from reynard.pipelines import Pipeline, reynard_pipeline
from reynard.dada import render_dada_header, make_dada_key_string

log = logging.getLogger("reynard.DspsrPipeline")
archive_match = "\d{4}-[0-1]\d-[0-3]\d-[0-2]\d:[0-5]\d:[0-6]\d{1}.ar$"

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
        self.observer = Observer()

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

        ###################
        ## Start up DSPSR
        ###################
        tstr = sensors["timestamp"]
        out_path = os.path.join("/output/",source_name,tstr)
        cmd = "dspsr {args} -N {source_name} {keyfile}".format(
            args=self._config["dspsr_params"]["args"],
            source_name=source_name,
            keyfile=dada_key_file.name)
        volumes = ["/tmp/:/tmp/",
                   "{}:/output/".format(
                    self._config["base_output_dir"])]
        log.debug("Running command: {0}".format(cmd))
        self._docker.run(
            self._config["dspsr_params"]["image"],
            cmd,
            detach=True,
            name="dspsr",
            ipc_mode="host",
            volumes=volumes,
            ulimits=self.ulimits,
            working_dir=out_path,
            requires_nvidia=True)


        ############################
        ## Start up PSRCHIVE monitor
        ############################

        volumes.append("/home/share:/home/share")
        out_dir = os.path.join("/home/share/monitors/timing/",source_name,tstr)
        try:
            os.makedirs(out_dir)
        except Exception as error:
            if error.errno != 17:
                raise error
        workdir = out_path
        psrchive = self._docker.run(
            self._config["psrchive_params"]["image"],
            detach=True,
            name="psrchive",
            cpuset_cpus="2",
            volumes=volumes,
            working_dir=workdir,
            tty=True,
            stdin_open=True)
        self.observer.schedule(ArchiveAdder(psrchive, out_dir), workdir, recursive=False)
        self.observer.start()

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
        self.observer.stop()
        self.observer.join()
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


class ArchiveAdder(FileSystemEventHandler):
    def __init__(self,psrchive,output_dir):
        super(ArchiveAdder,self).__init__()
        self.psrchive = psrchive
        self.output_dir = output_dir
        self.first_file = True

    def fscrunch(self,fname):
        self.psrchive.exec_run("pam -F -e Ft {}".format(fname))
        return fname.replace(".ar",".Ft")

    def process(self,fname):
        fscrunch_fname = self.fscrunch(fname)
        if self.first_file:
            shutil.copy2(fscrunch_fname,"sum.Ft")
            shutil.copy2(fname,"sum.fT")
            self.first_file = False
        else:
            self.psrchive.exec_run("psradd -T -inplace sum.fT {}".format(fname))
            self.psrchive.exec_run("psradd -inplace sum.tF {}".format(fscrunch_fname))
        shutil.copy2("sum.Ft",self.output_dir)
        shutil.copy2("sum.fT",self.output_dir)

    def on_created(self, event):
        try:
            fname = event.src_path
            if fname.endswith(".ar"):
                self.process(fname)
        except Exception as error:
            log.error(error)




