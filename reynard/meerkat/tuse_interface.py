import logging
import json
import tornado
import signal
from threading import Lock
from optparse import OptionParser
from katcp import Sensor, AsyncDeviceServer
from katcp.kattypes import request, return_reply, Int, Str, Discrete
from reynard.servers.ubi_server import UniversalBackendInterface

log = logging.getLogger("reynard.tuse_interface")

lock = Lock()

def is_power_of_two(n):
    """
    @brief  Test if number is a power of two

    @return True|False
    """
    return n != 0 and ((n & (n - 1)) == 0)

def next_power_of_two(n):
    """
    @brief  Round a number up to the next power of two
    """
    return 2**(n-1).bit_length()

class NodeUnavailable(Exception):
    pass

class Node(object):
    def __init__(self, hostname, port=5100, interfaces=None):
        self.hostname = hostname
        self.port = port
        self.interfaces = interfaces
        self.priority = 0


class NodeManager(object):
    """Wrapper class for managing node
        allocation and deallocation to subarray/products
        """
    def __init__(self, nodes):
        """
        @brief   Construct a new instance

        @param   nodes    An iterable container of Node objects
        """
        self._nodes = set(nodes)
        self._allocated = set()

    def allocate(self, count):
        """
        @brief    Allocate a number of nodes from the pool.

        @note     Free nodes will be allocated by priority order
                  with 0 being highest priority

        @return   A list of Node objects
        """
        with lock:
            log.debug("Request to allocate {} nodes".format(count))
            available_nodes = list(self._nodes.difference(self._allocated))
            log.debug("{} nodes available".format(len(available_nodes)))
            available_nodes.sort(key=lambda node: node.priority, reverse=True)
            if len(available_nodes) < count:
                raise NodeUnavailable("Cannot allocate {0} nodes, only {1} available".format(
                    count, len(available_nodes)))
            allocated_nodes = []
            for _ in range(count):
                node = available_nodes.pop()
                log.debug("Allocating node: {}".format(node.hostname))
                allocated_nodes.append(node)
                self._allocated.add(node)
            return allocated_nodes

    def deallocate(self,nodes):
        """
        @brief    Deallocate nodes and return the to the pool.

        @param    A list of Node objects
        """
        for node in nodes:
            log.debug("Deallocating node: {}".format(node.hostname))
            self._allocated.remove(node)

    def reset(self):
        """
        @brief   Deallocate all nodes
        """
        self._allocated = set()

    def available(self):
        """
        @brief   Return list of available nodes
        """
        return list(self._nodes.difference(self._allocated))

    def used(self):
        """
        @brief   Return list of allocated nodes
        """
        return list(self._allocated)


    @classmethod
    def from_json(cls,conf):
        """
        @brief     Construct a new NodeManager instance using a JSON object

        @detail    This class method takes a JSON object containing the configuration
                   for one or more nodes and populates the pool of nodes managed by
                   the NodeManager instance.
                   The format of the JSON should be (e.g.):
                   @code
                   [
                     {"host": "pacifix0", "port":5100, "nics": ["10.17.0.1", "10.17.0.2"], "priority":0},
                     {"host": "pacifix1", "port":5100, "nics": ["10.17.1.1", "10.17.1.2"], "priority":0},
                     {"host": "pacifix2", "port":5100, "nics": ["10.17.2.1", "10.17.2.2"], "priority":1},
                     {"host": "pacifix3", "port":5100, "nics": ["10.17.3.1", "10.17.3.2"], "priority":1},
                     {"host": "pacifix4", "port":5100, "nics": ["10.17.4.1", "10.17.4.2"], "priority":2},
                     {"host": "pacifix5", "port":5100, "nics": ["10.17.5.1", "10.17.5.2"]},
                     {"host": "pacifix6", "port":5100, "nics": ["10.17.6.1", "10.17.6.2"]},
                     {"host": "pacifix7", "port":5100, "nics": ["10.17.7.1", "10.17.7.2"]},
                     {"host": "pacifix8", "port":5100, "nics": ["10.17.8.1", "10.17.8.2"]},
                     {"host": "pacifix9", "port":5100, "nics": ["10.17.9.1", "10.17.9.2"]},
                     {"host": "paf0",     "port":5100, "nics": ["10.0.1.2", "10.0.5.100"], "priority":0},
                     {"host": "paf1",     "port":5100, "nics": ["10.0.1.3", "10.0.5.101"], "priority":0}
                   ]
                   @endcode
                   Note: This format is subject to change.

        @return     NodeManager object
        """
        node_confs = json.loads(conf)
        log.debug("Building NodeManager from JSON:\n{}".format(node_confs))
        nodes = []
        for conf in node_confs:
            node = Node(conf['host'], port=conf['port'],interfaces=conf['nics'])
            node.priority = conf.get('priority',3)
            log.debug("Adding node to pool: {}".format(node.hostname))
            nodes.append(node)
        return cls(nodes)


class TuseMasterController(AsyncDeviceServer):
    """The master pulsar backend control server for TUSE.
    """
    VERSION_INFO = ("reynard-tuse-api", 0, 1)
    BUILD_INFO = ("reynard-tuse-implementation", 0, 1, "rc1")

    # Standard for all equipment in MeerKAT
    DEVICE_STATUSES = ["ok", "degraded", "fail"]

    def __init__(self, ip, port, nodes_json, dummy=False):
        """
        @brief       Construct new TuseMasterController instance

        @params  ip       The IP address on which the server should listen
        @params  port     The port that the server should bind to
        @params  dummy    Specifies if the instance is running in a dummy mode

        @note   In dummy mode, the controller will act as a mock interface only, sending no requests to nodes.
                A valid node pool must still be provided to the instance, but this may point to non-existent nodes.

        """
        super(TuseMasterController, self).__init__(ip,port)
        self._node_pool = None
        self._products = {}
        self._dummy = dummy
        self._node_pool = NodeManager.from_json(nodes_json)

    def start(self):
        """Start TuseMasterController server"""
        super(TuseMasterController,self).start()


    def setup_sensors(self):
        """
        @brief    Set up monitoring sensors.

        @note     The following sensors are made available on top of defaul sensors
                  implemented in AsynDeviceServer and its base classes.

                  device-status:      Reports the health status of the FBFUSE and associated devices:
                                      Among other things report HW failure, SW failure and observation failure.

                  local-time-synced:  Indicates whether the local time of FBFUSE servers
                                      is synchronised to the master time reference (use NTP).
                                      This sensor is aggregated from all nodes that are part
                                      of FBF and will return "not sync'd" if any nodes are
                                      unsyncronised.

        """
        self._device_status = Sensor.discrete(
            "device-status",
            description="Health status of FBFUSE",
            params=self.DEVICE_STATUSES,
            default="ok",
            initial_status=Sensor.NOMINAL)
        self.add_sensor(self._device_status)

        self._local_time_synced = Sensor.boolean(
            "local-time-synced",
            description="Indicates FBF is NTP syncronised.",
            default=True,
            initial_status=Sensor.NOMINAL)
        self.add_sensor(self._local_time_synced)

        self._shit_giggles = Sensor.float(
            "shit-giggles",
            description="Shit-giggleness level from 0 to 1.",
            default=0.5,
            initial_status=Sensor.NOMINAL
            )
        self.add_sensor(self._shit_giggles)

    @request(Str(), Str())
    @return_reply()
    def request_configure(self, req, product_id, streams_json):
        """
        @brief      Configure FBFUSE to receive and process data from a subarray

        @detail     REQUEST ?configure product_id antennas_csv n_channels streams_json proxy_name
                    Configure FBFUSE for the particular data products

        @param      req               A katcp request object

        @param      product_id        This is a name for the data product, which is a useful tag to include
                                      in the data, but should not be analysed further. For example "array_1_bc856M4k".

        @param      antennas_csv      A comma separated list of physical antenna names used in particular sub-array
                                      to which the data products belongs.

        @param      n_channels        The integer number of frequency channels provided by the CBF.

        @param      streams_json      a JSON struct containing config keys and values describing the streams.

                                      For example:

                                      @code
                                         {'stream_type1': {
                                             'stream_name1': 'stream_address1',
                                             'stream_name2': 'stream_address2',
                                             ...},
                                             'stream_type2': {
                                             'stream_name1': 'stream_address1',
                                             'stream_name2': 'stream_address2',
                                             ...},
                                          ...}
                                      @endcode

                                      The steam type keys indicate the source of the data and the type, e.g. cam.http.
                                      stream_address will be a URI.  For SPEAD streams, the format will be spead://<ip>[+<count>]:<port>,
                                      representing SPEAD stream multicast groups. When a single logical stream requires too much bandwidth
                                      to accommodate as a single multicast group, the count parameter indicates the number of additional
                                      consecutively numbered multicast group ip addresses, and sharing the same UDP port number.
                                      stream_name is the name used to identify the stream in CAM.
                                      A Python example is shown below, for five streams:
                                      One CAM stream, with type cam.http.  The camdata stream provides the connection string for katportalclient
                                      (for the subarray that this FBFUSE instance is being configured on).
                                      One F-engine stream, with type:  cbf.antenna_channelised_voltage.
                                      One X-engine stream, with type:  cbf.baseline_correlation_products.
                                      Two beam streams, with type: cbf.tied_array_channelised_voltage.  The stream names ending in x are
                                      horizontally polarised, and those ending in y are vertically polarised.

                                      @code
                                         pprint(streams_dict)
                                         {'cam.http':
                                             {'camdata':'http://10.8.67.235/api/client/1'},
                                         {'cbf.antenna_channelised_voltage':
                                             {'i0.antenna-channelised-voltage':'spead://239.2.1.150+15:7148'},
                                          ...}
                                      @endcode

                                      If using katportalclient to get information from CAM, then reconnect and re-subscribe to all sensors
                                      of interest at this time.

        @param      proxy_name        The CAM name for the instance of the FBFUSE data proxy that is being configured.
                                      For example, "FBFUSE_3".  This can be used to query sensors on the correct proxy,
                                      in the event that there are multiple instances in the same subarray.

        @note       A configure call will result in the generation of a new subarray instance in FBFUSE that will be added to the clients list.

        @return     katcp reply object [[[ !configure ok | (fail [error description]) ]]]
        """
        # Test if product_id already exists
        if product_id in self._products:
            return ("fail", "FBF already has a configured product with ID: {}".format(product_id))
        # Determine number of nodes required based on number of antennas in subarray
        # Note this is a poor way of handling this that may be updated later. In theory
        # there is a throughput measure as a function of bandwidth, polarisations and number
        # of antennas that allows one to determine the number of nodes to run. Currently we
        # just assume one antennas worth of data per NIC on our servers, so two antennas per
        # node.

        streams = json.loads(streams_json)
        product = streams
        self._products[product_id] = product
        return ("ok",)

    @request(Str())
    @return_reply()
    def request_deconfigure(self, req, product_id):
        """
        @brief      Deconfigure the FBFUSE instance.

        @note       Deconfigure the FBFUSE instance. If FBFUSE uses katportalclient to get information
                    from CAM, then it should disconnect at this time.

        @param      req               A katcp request object

        @param      product_id        This is a name for the data product, used to track which subarray is being deconfigured.
                                      For example "array_1_bc856M4k".

        @return     katcp reply object [[[ !deconfigure ok | (fail [error description]) ]]]
        """
        # Test if product exists
        if product_id not in self._products:
            return ("fail", "No product configured with ID: {}".format(product_id))
        product = self._products[product_id]
        try:
            product.deconfigure()
        except Exception as error:
            return ("fail", str(error))
        self._node_pool.deallocate(product.nodes)
        del self._products[product_id]
        return ("ok",)

    @request(Str())
    @return_reply()
    def request_capture_init(self, req, product_id):
        """
        @brief      Prepare FBFUSE ingest process for data capture.

        @note       A successful return value indicates that FBFUSE is ready for data capture and
                    has sufficient resources available. An error will indicate that FBFUSE is not
                    in a position to accept data

        @param      req               A katcp request object

        @param      product_id        This is a name for the data product, used to track which subarray is being told to start capture.
                                      For example "array_1_bc856M4k".

        @return     katcp reply object [[[ !capture-init ok | (fail [error description]) ]]]
        """
        if product_id not in self._products:
            return ("fail", "No product configured with ID: {}".format(product_id))
        product = self._products[product_id]
        try:
            product.capture_init()
        except Exception as error:
            return ("fail",str(error))
        else:
            return ("ok",)

    @request(Str())
    @return_reply()
    def request_capture_done(self, req, product_id):
        """
        @brief      Terminate the FBFUSE ingest process for the particular FBFUSE instance

        @note       This writes out any remaining metadata, closes all files, terminates any remaining processes and
                    frees resources for the next data capture.

        @param      req               A katcp request object

        @param      product_id        This is a name for the data product, used to track which subarray is being told to stop capture.
                                      For example "array_1_bc856M4k".

        @return     katcp reply object [[[ !capture-done ok | (fail [error description]) ]]]
        """
        if product_id not in self._products:
            return ("fail", "No product configured with ID: {}".format(product_id))
        product = self._products[product_id]
        try:
            product.capture_done()
        except Exception as error:
            return ("fail",str(error))
        else:
            return ("ok",)

    @request()
    @return_reply(Int())
    def request_products_list(self, req):
        """
        @brief      List all currently registered products and their states

        @param      req               A katcp request object

        @note       The details of each product are provided via an #inform
                    as a JSON string containing information on the product state.
                    For example:

                    @code
                    {'array_1_bc856M4k':{'status':'configured','nodes':['fbf00','fbf01']}}
                    @endcode

        @return     katcp reply object [[[ !capture-done ok | (fail [error description]) <number of configured products> ]]],
        """
        for product_id,product in self._products.items():
            info = {}
            info[product_id] = {}
            info[product_id]['status'] = "capturing" if product.capturing else "configured"
            info[product_id]['nodes'] = [i.hostname for i in product.nodes]
            as_json = json.dumps(info)
            req.inform(as_json)
        return ("ok",len(self._products))


class TuseProductController(object):
    """
    Wrapper class for an FBFUSE product. Objects of this type create a UBI server instance and
    allocate nodes to this. The intention here is to have a class that translates information
    specific to MeerKAT into a general configuration and pipeline deployment tool as is done
    for Effelsberg.
    """
    def __init__(self, product_id, antennas, n_channels, streams, proxy_name, nodes):
        """
        @brief      Construct new instance

        @param      product_id        The name of the product

        @param      antennas_csv      A list of antenna names

        @param      n_channels        The integer number of frequency channels provided by the CBF.

        @param      streams           A dictionary containing config keys and values describing the streams.
        """
        self._product_id = product_id
        self._antennas = antennas
        self._n_channels = n_channels
        self._streams = streams
        self._proxy_name = proxy_name
        self._nodes = nodes
        self._capturing = False
        self._client = None
        self._server = None

    @property
    def nodes(self):
        return self._nodes

    @property
    def capturing(self):
        return self._capturing

    def start(self):
        name = "{}_ubi_client".format(self._product_id)
        log.debug("Starting UBI server for product {}".format(self._product_id))
        self._server = UniversalBackendInterface("127.0.0.1",0) # 0 = random available port above 32k
        self._server.start()
        """
        self._client = KATCPClientResource(dict(
            name=name,
            address=self._server.bind_address(),
            controlled=True))
        """
        for node in self._nodes:
            self._server._add_node(node['host'],node['host'],node['port'])

    def configure(self):
        """
        @brief      Configure the nodes for processing
        """
        pass

    def deconfigure(self):
        """
        @brief      Deconfigure the nodes
        """
        pass

    def capture_init(self):
        """
        @brief      Begin a data capture
        """
        pass

    def capture_done(self):
        """
        @brief      End a data capture
        """
        pass


@tornado.gen.coroutine
def on_shutdown(ioloop, server):
    log.info("Shutting down server")
    yield server.stop()
    ioloop.stop()

def main():
    test_nodes = '''
    [
    {"priority": 1, "nics": [], "host": "fbf00", "port": 5100},
    {"priority": 4, "nics": [], "host": "fbf01", "port": 5100},
    {"priority": 3, "nics": [], "host": "fbf02", "port": 5100},
    {"priority": 0, "nics": [], "host": "fbf03", "port": 5100},
    {"priority": 4, "nics": [], "host": "fbf04", "port": 5100},
    {"priority": 1, "nics": [], "host": "fbf05", "port": 5100},
    {"priority": 1, "nics": [], "host": "fbf06", "port": 5100},
    {"priority": 4, "nics": [], "host": "fbf07", "port": 5100},
    {"priority": 0, "nics": [], "host": "fbf08", "port": 5100},
    {"priority": 0, "nics": [], "host": "fbf09", "port": 5100},
    {"priority": 0, "nics": [], "host": "fbf10", "port": 5100},
    {"priority": 2, "nics": [], "host": "fbf11", "port": 5100},
    {"priority": 0, "nics": [], "host": "fbf12", "port": 5100},
    {"priority": 4, "nics": [], "host": "fbf13", "port": 5100},
    {"priority": 1, "nics": [], "host": "fbf14", "port": 5100},
    {"priority": 2, "nics": [], "host": "fbf15", "port": 5100},
    {"priority": 1, "nics": [], "host": "fbf16", "port": 5100},
    {"priority": 4, "nics": [], "host": "fbf17", "port": 5100},
    {"priority": 2, "nics": [], "host": "fbf18", "port": 5100},
    {"priority": 3, "nics": [], "host": "fbf19", "port": 5100},
    {"priority": 4, "nics": [], "host": "fbf20", "port": 5100},
    {"priority": 4, "nics": [], "host": "fbf21", "port": 5100},
    {"priority": 0, "nics": [], "host": "fbf22", "port": 5100},
    {"priority": 3, "nics": [], "host": "fbf23", "port": 5100},
    {"priority": 3, "nics": [], "host": "fbf24", "port": 5100},
    {"priority": 1, "nics": [], "host": "fbf25", "port": 5100},
    {"priority": 3, "nics": [], "host": "fbf26", "port": 5100},
    {"priority": 0, "nics": [], "host": "fbf27", "port": 5100},
    {"priority": 3, "nics": [], "host": "fbf28", "port": 5100},
    {"priority": 0, "nics": [], "host": "fbf29", "port": 5100},
    {"priority": 0, "nics": [], "host": "fbf30", "port": 5100},
    {"priority": 2, "nics": [], "host": "fbf31", "port": 5100}
    ]
    '''

    usage = "usage: %prog [options]"
    parser = OptionParser(usage=usage)
    parser.add_option('-H', '--host', dest='host', type=str,
        help='Host interface to bind to')
    parser.add_option('-p', '--port', dest='port', type=long,
        help='Port number to bind to')
    parser.add_option('', '--log_level',dest='log_level',type=str,
        help='Port number of status server instance',default="INFO")
    parser.add_option('', '--dummy',action="store_true", dest='dummy',
        help='Set status server to dummy')
    parser.add_option('-n', '--nodes',dest='nodes', type=str, default=None,
        help='Path to file containing list of available nodes')
    (opts, args) = parser.parse_args()
    FORMAT = "[ %(levelname)s - %(asctime)s - %(filename)s:%(lineno)s] %(message)s"
    logger = logging.getLogger('reynard')
    logging.basicConfig(format=FORMAT)
    logger.setLevel(opts.log_level.upper())
    ioloop = tornado.ioloop.IOLoop.current()
    log.info("Starting TuseMasterController instance")

    if opts.nodes is not None:
        with open(opts.nodes) as f:
            nodes = f.read()
    else:
        nodes = test_nodes

    server = TuseMasterController(opts.host, opts.port, nodes, dummy=opts.dummy)
    signal.signal(signal.SIGINT, lambda sig, frame: ioloop.add_callback_from_signal(
        on_shutdown, ioloop, server))

    def start_and_display():
        server.start()
        log.info("Listening at {0}, Ctrl-C to terminate server".format(server.bind_address))
    ioloop.add_callback(start_and_display)
    ioloop.start()

if __name__ == "__main__":
    main()
