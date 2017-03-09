"""
Wrappers for generic compute pipelines on a node
"""
import logging
import shlex
import subprocess as sub

NOT_STARTED, RUNNING, FAILED, COMPLETED = range(4)
STATES = {
    NOT_STARTED: "not started",
    RUNNING: "running",
    FAILED: "failed",
    COMPLETED: "completed"
}

log = logging.getLogger("reynard.pipeline")

class Process(object):
    def __init__(self,cmd):
        self.cmd = cmd

    def start(self):
        args = shlex.split(self.cmd)
        self._process = sub.Popen(args, stdout=sub.PIPE, stderr=sub.PIPE)

    def status(self):
        if self._process is None:
            return NOT_STARTED
        if self._process.poll() is None:
            return RUNNING
        elif self._process.poll() != 0:
            return FAILED
        elif self._process.poll() == 0:
            return COMPLETED

    def kill(self):
        if self.status() is RUNNING:
            self._process.terminate()
            self._process.wait()

    def wait(self):
        self._process.wait()

    def restart(self):
        self.kill()
        self.start()

    def __str__(self):
        retval = "" if self._process.returncode in [None,0] else "(return code: {code})".format(code=self._process.returncode)
        state = STATES[self.status()]
        return "'{self.cmd}' {state} {retval}".format(**locals())



class Pipeline(object):
    def configure(self,config):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError

    def run(self):
        raise NotImplementedError

    def cleanup(self):
        raise NotImplementedError

    def status(self):
        raise NotImplementedError

    def log(self):
        raise NotImplementedError

class DockerPipeline(Pipeline):
    def __init__(self):
        self.containers = []
        super(DockerPipeline,self).__init__()

    def log(self):
        logs = {}
        for container in self.containers():
            logs[container.name] = client





