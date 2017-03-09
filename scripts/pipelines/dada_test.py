import docker
import logging
from requests import ReadTimeout
from docker.errors import ContainerError, NotFound

client = docker.from_env()

log = logging.getLogger("TestPipeline")

class TestPipeline(object):
    def __init__(self, config_dir):
        self._volumes = {
            config_dir: {
                'bind': '/config/',
                'mode': 'ro'
            }
        }
        self._containers = ["junkdb","dbmonitor","dbnull"]
        self._is_entered = False

    def _dada(self,cmd,**kwargs):
        try:
            log.info("Running psr-capture container: {cmd}".format(cmd=cmd))
            return client.containers.run("psr-capture",cmd,ipc_mode="host",**kwargs)
        except Exception as e:
            log.warning("Container error: {msg}".format(msg=str(e)))
            return None

    def __enter__(self):
        self._is_entered = True
        log.info("Creating dada buffer")
        self.stop()
        self._dada("dada_db -k dada -n 8 -b 16000000",remove=True)
        return self

    def run(self):
        if not self._is_entered:
            raise Exception("Must use with-statement syntax")
        self._dada("dada_dbnull -k dada", detach=True, name="dbnull")
        self._dada("dada_junkdb -k dada -r 64 -t 100 -g /config/header0.txt",
            detach=True, volumes=self._volumes, name="junkdb")
        self._dada("dada_dbmonitor -k dada", detach=True, name="dbmonitor")
        running,status = self.status()
        if not running:
            raise Exception("Pipeline did not start correctly: {status}".format(status=status))

    def status(self):
        running = True
        status = {}
        for name in self._containers:
            try:
                container = client.containers.get(name)
            except NotFound:
                status[name] = {"status":"failed", "info":"container not found"}
                running = False
                continue
            if not container.status == "running":
                status[name] = {"status":"failed", "info":container.logs()}
                running = False
            else:
                status[name] = {"status":"running", "info":""}
        return running,status

    def stop(self):
        for name in self._containers:
            try:
                container = client.containers.get(name)
            except NotFound:
                continue
            if container.status == 'running':
                log.info("Killing {name} container".format(name=name))
                container.kill()
            log.info("Removing {name} container".format(name=name))
            container.remove()

    def __exit__(self, type, value, traceback):
        self.stop()
        log.info("Destroying dada buffer")
        self._dada("dada_db -d -k dada", remove=True)

if __name__ == "__main__":
    import time
    logging.basicConfig()
    log.setLevel(logging.DEBUG)
    conf = "/Users/ebarr/Soft/MeerKAT/MGMT/reynard/scripts/pipelines"
    with TestPipeline(conf) as pipeline:
        pipeline.run()
        time.sleep(10)
        print pipeline.status()
        time.sleep(2)





