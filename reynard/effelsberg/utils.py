import jinja2
from tornado.gen import coroutine, Return
from reynard.utils.dada import dada_defaults, DADA_HEADER


@coroutine
def get_dada_header(sensors):
    """
    @brief      Gets the dada header.

    @param      sensors  The sensors

    @return     The dada header.
    """
    updates = {}
    scannum = yield sensors.scannum.get_value()
    subscannum = yield sensors.subscannum.get_value()
    project = yield sensors.project.get_value()
    updates["obs_id"] = "{0}_{1}_{2}".format(scannum, subscannum, project)
    updates["source_name"] = yield sensors.source.get_value()
    updates["ra"] = yield sensors.ra.get_value()
    updates["dec"] = yield sensors.ra.get_value()
    receiver = yield sensors.receiver.get_value()
    focus = yield sensors.focus.get_value()
    focus_str = "P" if focus == "primary" else "S"
    wavelength, version = receiver.split(".")
    updates["receiver"] = "{0}{1}-{2}".format(focus_str, wavelength, version)
    header = dada_defaults()
    header.update(updates)
    raise Return(jinja2.Template(DADA_HEADER.lstrip()).render(**header))
