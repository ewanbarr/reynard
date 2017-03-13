import logging
import json
from docker.errors import ContainerError, NotFound, APIError
from reynard.pipelines import Pipeline, reynard_pipeline, DockerHelper, PipelineError

log = logging.getLogger("reynard.TestPipeline")

@reynard_pipeline("TestPipeline")
class Junk2Db2Null(Pipeline):
    def __init__(self):
        super(Junk2Db2Null,self).__init__()
        self._volumes = None
        self._docker = DockerHelper()

    def _configure(self, config):
        config = str(config)
        try:
            self._config = json.loads(config)
            self._volumes = ["{0}:/config/:ro".format(self._config["config_path"])]
        except Exception as error:
            raise PipelineError("Could not parse configuration [error: {0}]".format(str(error)))
        try:
            self._deconfigure()
        except Exception as error:
            pass
        log.debug("Creating dada buffer")
        self._docker.run("psr-capture","dada_db -k dada -n 8 -b 16000000",remove=True, ipc_mode="host")

    def _start(self):
        self._set_watchdog("dbnull",True)
        self._set_watchdog("junkdb",False)
        self._set_watchdog("dbmonitor",True)
        self._docker.run("psr-capture", "dada_dbnull -k dada",
            detach=True, name="dbnull", ipc_mode="host")
        self._docker.run("psr-capture", "dada_junkdb -k dada -r 64 -t 15 -g /config/header0.txt",
            detach=True, volumes=self._volumes, name="junkdb", ipc_mode="host")
        self._docker.run("psr-capture", "dada_dbmonitor -k dada",
            detach=True, name="dbmonitor", ipc_mode="host")

    def _stop(self):
        for name in ["dbnull","junkdb","dbmonitor"]:
            container = self._docker.get(name)
            try:
                log.debug("Stopping {name} container".format(name=container.name))
                container.kill()
            except APIError:
                pass
            try:
                log.debug("Removing {name} container".format(name=container.name))
                container.remove()
            except:
                pass

    def _deconfigure(self):
        log.debug("Destroying dada buffer")
        self._docker.run("psr-capture", "dada_db -d -k dada",
            remove=True, ipc_mode="host")

    def _status(self):
        reply = {}
        reply["state"] = self.state
        if self.state == "running":
            container_info = []
            for name in ["dbnull","junkdb","dbmonitor"]:
                container = self._docker.get(name)
                detail = {
                "name":container.name,
                "status":container.status,
                "procs":container.top(),
                "logs":container.logs(tail=20)
                }
                container_info.append(detail)
            reply["info"] = container_info
        return reply

if __name__ == "__main__":
    import time
    import pprint
    def state_change(state, pipeline):
        log.debug("{0} pipeline state: {1}".format(
            pipeline.__class__.__name__, state))

    def status_printer(status):
        for info in status:
            print "-"*50
            print "Container: {0}".format(info["name"])
            print "Status: {0}".format(info["status"])
            if info['procs']:
                print "Processes:"
                print "\t".join(info["procs"]["Titles"])
                for process in info["procs"]["Processes"]:
                    print "\t".join(process)
            if info['logs']:
                print "Logs:"
                print info['logs']

    FORMAT = "[ %(levelname)s - %(asctime)s - %(filename)s:%(lineno)s] %(message)s"
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
    status = pipeline.status()
    status_printer(status)
    time.sleep(3)
    pipeline.stop()
    pipeline.deconfigure()






