"""
Wrappers for generic compute pipelines on a node
"""
import logging
import docker
from threading import Thread, Event, Lock

log = logging.getLogger("reynard.pipelines")

STATES = ["idle","configuring","ready",
    "starting","running","stopping",
    "deconfiguring","failed"]

class Enum(object):
    def __init__(self,vals):
        for ii,val in enumerate(vals):
            self.__setattr__(val.upper(),val)

IDLE, READY, RUNNING, FAILED, COMPLETED = range(5)
STATES = {
    IDLE: "Idle",
    READY: "Ready",
    RUNNING: "Running",
    FAILED: "Failed",
    COMPLETED: "Completed"
}

NVIDA_DOCKER_PLUGIN_HOST = "localhost:3476"

PIPELINE_REGISTRY = {}

class PipelineError(Exception):
    pass

def reynard_pipeline(name,description="",version="",requires_nvidia=False):
    def wrap(cls):
        if PIPELINE_REGISTRY.has_key(name):
            log.warning("Conflicting pipeline names '{0}'".format(name))
        PIPELINE_REGISTRY[name] = {
        "description":description,
        "version":version,
        "requires_nvidia":requires_nvidia
        }
        return cls
    return wrap

def nvidia_config(addr=NVIDA_DOCKER_PLUGIN_HOST):
    url = 'http://{0}/docker/cli/json'.format(addr)
    resp = urllib2.urlopen(url).read().decode()
    config = json.loads(resp)
    params = {
    "devices":config["Devices"],
    "volume_driver":config["VolumeDriver"],
    "volumes":config["Volumes"]
    }
    return params

class Watchdog(Thread):
    def __init__(self, name, standdown, callback, persistent=False):
        Thread.__init__(self)
        self._client = docker.from_env()
        self._name = name
        self._disable = standdown
        self._callback = callback
        self.daemon = True

    def _is_dead(self,event):
        return (event["Type"] == "container"
            and event["Actor"]["Attributes"]["name"] == self._name
            and event["status"] == "die")

    def run(self):
        log.debug("Setting watchdog on container '{0}'".format(self._name))
        for event in self._client.events(decode=True):
            if self._disable.is_set():
                log.debug("Watchdog standing down on container '{0}'".format(self._name))
                break
            elif self._is_dead(event):
                exit_code = event["Actor"]["Attributes"]["exitCode"]
                log.debug("Watchdog activated on container '{0}'".format(self._name))
                self._callback(exit_code)


class Stateful(object):
    def __init__(self, initial_state):
        self._state = initial_state
        self._registry = []
        self._state_lock = Lock()

    def register_callback(self,callback):
        self._registry.append(callback)

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self,value):
        with self._state_lock:
            self._state = value
            for callback in self._registry:
                callback(self._state,self)


class Pipeline(Stateful):
    def __init__(self):
        self._watchdogs = []
        self._standdown = Event()
        self._lock = Lock()
        super(Pipeline,self).__init__("idle")

    def _set_watchdog(self, name, persistent=False):
        def callback(exit_code):
            if persistent or exit_code != 0:
                self.stop(failed=True)
        guard = Watchdog(name,self._standdown,callback)
        guard.start()
        self._watchdogs.append(guard)

    def _call(self,next_state,func,*args,**kwargs):
        try:
            func(*args,**kwargs)
        except Exception as error:
            log.exception(str(error))
            self.state = "failed"
        else:
            self.state = next_state

    def configure(self,config):
        with self._lock:
            log.info("Configuring pipeline")
            if self.state != "idle":
                raise PipelineError("Can only configure pipeline in idle state")
            self.state = "configuring"
            self._call("ready",self._configure,config)

    def _configure(self,config):
        raise NotImplementedError

    def stop(self,failed=False):
        post_state = "failed" if failed else "ready"
        with self._lock:
            log.info("Stopping pipeline {0}".format("(failure)" if failed else ""))
            if self.state != "running" and not failed:
                raise PipelineError("Can only stop a running pipeline")
            self.state = "stopping"
            self._standdown.set()
            self._watchdogs = []
            self._call(post_state,self._stop)

    def _stop(self):
        raise NotImplementedError

    def start(self):
        with self._lock:
            log.info("Starting pipeline")
            if self.state != "ready":
                raise PipelineError("Pipeline can only be started from ready state")
            self.state = "starting"
            self._call("running",self._start)

    def _start(self):
        raise NotImplementedError

    def deconfigure(self):
        with self._lock:
            log.info("Deconfiguring pipeline")
            if self.state != "ready":
                raise PipelineError("Pipeline can only be deconfigured from ready state")
            self.state = "deconfiguring"
            self._call("idle",self._deconfigure)

    def _deconfigure(self):
        raise NotImplementedError

    def status(self):
        with self._lock:
            try:
                return self._status()
            except Exception as error:
                log.error(str(error))

    def _status(self):
        raise NotImplementedError


class DockerHelper(object):
    def __init__(self):
        self._client = docker.from_env()

    def run(self, *args, **kwargs):
        return self._client.containers.run(*args,**kwargs)

    def run_nvidia(self, *args, **kwargs):
        kwargs.update(nvidia_config())
        return _run_container(*args,**kwargs)




