import logging

log = logging.getLogger("reynard.tuse_interface.callback_handler")

class CallbackMessageData(dict):
    """
    Convenience class to parse and manipulate dictionaries passed as the argument of the
    callback function of a KATPortalClient instance.

    Example: if "items" is the argument to the callback function, then we can write
        mdata = CallbackMessageData(items)
        mdata.name  # sensor name
        mdata.value # sensor value
    """
    def __init__(self, items):
        super(CallbackMessageData, self).__init__(items["msg_data"])

    def __getattr__(self, name):
        return self[name]



class TuseCallbackHandler(object):
    """
    """
    def __init__(self, product_controller=None, fbfuse_proxy_name="fbfuse_1"):
        """
        Parameters:
        -----------
            product_controller: TuseProductController
                Parent TuseProductController object.
            fbfuse_proxy_name: str
                Name of the FBFUSE proxy, something like "fbfuse_1"
        """
        # Sensor names are formatted like
        # {FBFUSE_PROXY_NAME}_{SENSOR_NAME}
        self.product_controller = product_controller
        self.fbfuse_proxy_name = fbfuse_proxy_name
        self.sensor_name_prefix = fbfuse_proxy_name + "_"
        self.fbfuse_sensors = {}

    def __call__(self, items):
        return self.handle(items)

    def device_status_handler(self, cmdata):
        log.debug("device_status_handler() has been called.")
        fbfuse_device_status = cmdata.value.lower()

        # Now pretend to do something based on that sensor value, as a test
        if fbfuse_device_status == "ok":
            log.debug("fbfuse_device_status is now OK.")
            self.product_controller.capture_init()
        else:
            log.debug("fbfuse_device_status is now \"{:s}\"".format(fbfuse_device_status))
            self.product_controller.capture_done()

    def get_unprefixed_sensor_name(self, full_sensor_name):
        return full_sensor_name.split(self.sensor_name_prefix)[-1]

    def get_handler(self, sensor_name):
        handler_name = sensor_name + "_handler"
        try:
            handler = getattr(self, handler_name)
            return handler
        except AttributeError:
            return None

    def handle(self, items):
        log.debug("Handling callback argument: {!s}".format(items))
        cmdata = CallbackMessageData(items)
        full_sensor_name = cmdata.name

        # Ignore sensors whose name do not start with "{FBFUSE_PROXY_NAME}_"
        # e.g. "fbfuse_1_"
        if not full_sensor_name.startswith(self.sensor_name_prefix):
            return

        # Get un-prefixed sensor name
        uname = self.get_unprefixed_sensor_name(full_sensor_name)
        handler = self.get_handler(uname)

        # Update FBFUSE state tracker
        self.fbfuse_sensors[uname] = cmdata.value

        # Do what needs to be done based on the sensor update we received
        if handler is not None:
            handler(cmdata)
        else:
            log.debug("No handler available for sensor name \"{:s}\"".format(uname))


class MockTuseProductController(object):
    """ """
    def __init__(self):
        pass

    def capture_init(self):
        print("Starting data capture and processing ...")

    def capture_done(self):
        print("Ending data capture and processing ...")



if __name__ == "__main__":
    FORMAT = "[ %(levelname)s - %(asctime)s - %(filename)s:%(lineno)s] %(message)s"
    logger = logging.getLogger('reynard.tuse_interface.callback_handler')
    logging.basicConfig(format=FORMAT)
    logger.setLevel("DEBUG")


    items_device_status_ok = {
        "msg_pattern": "namespace_533647d4-7e6b-4b41-85f3-94e50c6b1322:fbfuse_1*",
        "msg_channel": "namespace_533647d4-7e6b-4b41-85f3-94e50c6b1322:fbfuse_1_device_status",
        "msg_data": {
            "status": "nominal",
            "timestamp": 1512749004.352641,
            "value": "ok",
            "name": "fbfuse_1_device_status",
            "received_timestamp": 1516026591.31986
            }
        }

    items_device_status_fail = {
        "msg_pattern": "namespace_533647d4-7e6b-4b41-85f3-94e50c6b1322:fbfuse_1*",
        "msg_channel": "namespace_533647d4-7e6b-4b41-85f3-94e50c6b1322:fbfuse_1_device_status",
        "msg_data": {
            "status": "nominal",
            "timestamp": 1512749004.352641,
            "value": "fail",
            "name": "fbfuse_1_device_status",
            "received_timestamp": 1516026591.31986
            }
        }

    items2 = {
        "msg_pattern": "namespace_533647d4-7e6b-4b41-85f3-94e50c6b1322:fbfuse_1*",
        "msg_channel": "namespace_533647d4-7e6b-4b41-85f3-94e50c6b1322:fbfuse_1_fbfmc_address",
        "msg_data": {
            "status": "nominal",
            "timestamp": 1512739165.495304,
            "value": [
                "192.168.4.60",
                5000
            ],
            "name": "fbfuse_1_fbfmc_address",
            "received_timestamp": 1516026591.333353
            }
        }

    ch = TuseCallbackHandler(
        product_controller=MockTuseProductController(),
        fbfuse_proxy_name="fbfuse_1")

    ch(items_device_status_ok)
    ch(items_device_status_fail)

