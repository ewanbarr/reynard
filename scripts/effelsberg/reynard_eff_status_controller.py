import Tkinter as tk
import warnings
from collections import OrderedDict
import tornado
from katcp.resource_client import KATCPClientResource
from reynard.effelsberg.servers import EFF_JSON_CONFIG
from reynard.gui import ParameterController

class SensorParameterController(ParameterController):
    def __init__(self, parent, key, value, client):
        ParameterController.__init__(self, parent, key, value)
        self._set = tk.Button(self,text="Set",command=self.set_sensor)
        self._set.pack(side=tk.LEFT,expand=1)
        self.client = client

    def set_sensor(self):
        self.client.req.sensor_set(key,str(self.get()))


class EffelsbergStatusController(tk.Frame):
    def __init__(self, parent, client):
        tk.Frame.__init__(self, parent)
        self._params = {}
        self.client = client
        self.build()

    def build(self):
        controller = SensorParameterController(self,'observing',1, self.client)
        controller.pack()


if __name__ == "__main__":
    test_dict = {}
    keys = ["scannum","observing","ra","dec"]
    for key in keys:
        param = EFF_JSON_CONFIG[key]
        test_dict[key] = param["default"]

    ioloop = tornado.ioloop.IOLoop.current()
    client = KATCPClientResource(dict(
        name="web-interface-client",
        address=("localhost", 5000),
        controlled=True))
    ioloop.add_callback(client.start)
    root = tk.Tk()
    c = EffelsbergStatusController(root,client)
    c.pack()
    ioloop.add_callback(root.mainloop)
    #root.mainloop()
    ioloop.start()