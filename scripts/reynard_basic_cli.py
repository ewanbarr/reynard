#!/usr/bin/env python

"""KATCP command line client example.

   copyright (c) 2008 SKA/KAT. All Rights Reserved.
   @author Simon Cross <simon.cross@ska.ac.za>
   @date 2008-10-29
"""

import logging
import sys
import traceback
from optparse import OptionParser
import katcp
import cPickle

from katcp import DeviceClient

logging.basicConfig(level=logging.INFO,
                    stream=sys.stderr,
                    format="%(asctime)s - %(name)s - %(filename)s:"
                    "%(lineno)s - %(levelname)s - %(message)s")

class FbfuseCmdlineClient(DeviceClient):

    def reply_multicast_beam_mapping(self,msg):
        """arse"""
        response,data = msg.arguments
        mapping = cPickle.loads(data)
        print mapping

    def unhandled_reply(self,msg):
        """Deal with unhandled replies"""
        print "Unhandled reply:",msg

    def unhandled_inform(self,msg):
        """Deal with unhandled replies"""
        print "Unhandled inform:",msg

    def unhandled_request(self,msg):
        """Deal with unhandled replies"""
        print "Unhandled request:",msg


if __name__ == "__main__":

    usage = "usage: %prog [options]"
    parser = OptionParser(usage=usage)
    parser.add_option('-a', '--host', dest='host', type="string", default="", metavar='HOST',
                      help='attach to server HOST (default="" - localhost)')
    parser.add_option('-p', '--port', dest='port', type=int, default=1235, metavar='N',
                      help='attach to server port N (default=1235)')
    (opts, args) = parser.parse_args()

    katcp_parser = katcp.MessageParser()

    print "Client connecting to port %s:%d, Ctrl-C to terminate." % (opts.host, opts.port)
    client = FbfuseCmdlineClient(opts.host, opts.port)

    client.start()
    try:
        while True:
            s = raw_input("> ")
            try:
                msg = katcp_parser.parse(s)
                client.ioloop.add_callback(client.send_message, msg)
            except Exception, e:
                e_type, e_value, trace = sys.exc_info()
                reason = "\n".join(traceback.format_exception(
                    e_type, e_value, trace, 20
                ))
                print reason
    finally:
        client.stop()
        client.join()
