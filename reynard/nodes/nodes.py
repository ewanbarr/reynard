import logging
import json
from threading import Lock

log = logging.getLogger("reynard.nodes")

lock = Lock()

class NodeUnavailable(Exception):
    pass

class Node(object):
    """Wrapper class for metadata pertaining to a compute node.

    Note: This could/should be replaced by a simple dictionary
    """
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

        @return    NodeManager object
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