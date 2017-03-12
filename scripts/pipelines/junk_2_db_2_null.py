import logging
import json
from docker.errors import ContainerError, NotFound, APIError
from reynard.pipelines import Pipeline, reynard_pipeline, DockerHelper

log = logging.getLogger("reynard.TestPipeline")

@reynard_pipeline("TestPipeline")
class Junk2Db2Null(Pipeline):
    def __init__(self):
        super(Junk2Db2Null,self).__init__()
        self._volumes = None
        self._docker = DockerHelper()
        self._active = []

    def _configure(self, config):
        self._config = json.loads(config)
        self._volumes = ["{0}:/config/:ro".format(self._config["config_path"])]
        try:
            self._deconfigure()
        except ContainerError as error:
            pass
        log.info("Creating dada buffer")
        self._docker.run("psr-capture","dada_db -k dada -n 8 -b 16000000",remove=True, ipc_mode="host")

    def _start(self):
        self._active.append(self._docker.run("psr-capture", "dada_dbnull -k dada",
            detach=True, name="dbnull", ipc_mode="host"))
        self._active.append(self._docker.run("psr-capture", "dada_junkdb -k dada -r 64 -t 100 -g /config/header0.txt",
            detach=True, volumes=self._volumes, name="junkdb", ipc_mode="host"))
        self._active.append(self._docker.run("psr-capture", "dada_dbmonitor -k dada",
            detach=True, name="dbmonitor", ipc_mode="host"))

    def _stop(self):
        for container in self._active:
            try:
                log.info("Stopping {name} container".format(name=container.name))
                container.kill()
            except APIError:
                pass
            log.info("Removing {name} container".format(name=container.name))
            container.remove()
        self._active = []

    def _deconfigure(self):
        log.info("Destroying dada buffer")
        self._docker.run("psr-capture", "dada_db -d -k dada",
            remove=True, ipc_mode="host")

    def status(self):
        container_info = []
        for container in self._active:
            detail = {
            "name":container.name,
            "status":container.status,
            "procs":container.top(),
            "logs":container.logs(tail=20)
            }
            container_info.append(detail)
        return container_info

if __name__ == "__main__":
    import time
    import pprint
    def state_change(state, pipeline):
        log.debug("{0} pipeline state: {1}".format(
            pipeline.__class__.__name__, state))

    FORMAT = "[%(filename)s:%(lineno)s - %(funcName)20s() ] %(message)s"
    logger = logging.getLogger('reynard')
    logging.basicConfig(format=FORMAT)
    logger.setLevel(logging.DEBUG)
    config = json.dumps(
        {"config_path":"/Users/ebarr/Soft/MeerKAT/MGMT/reynard/scripts/pipelines"})
    pipeline = Junk2Db2Null()
    pipeline.register_callback(state_change)
    pipeline.configure(config)
    pipeline.start()
    time.sleep(3)
    pprint.pprint(pipeline.status())
    time.sleep(3)
    pipeline.stop()
    pipeline.deconfigure()






