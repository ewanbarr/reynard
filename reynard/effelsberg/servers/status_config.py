### any updater functions that can't be made into lambdas should go here ###

EFF_JSON_CONFIG = {
    "lmst": {"type":"float", "units":"hours", "default":0.0,
                "description":"Local mean sidereal time (LMST)",
                "updater":lambda data: data["hourangle"]},
    "ha": {"type":"float", "units":"degrees", "default":0.0,
           "description":"Hour Angle",
           "updater":lambda data: data["hourangle"]},
    "utc": {"type":"float", "units":"hours", "default":0.0,
            "description":"Coordinated Universal Time",
            "updater":lambda data: data["mjuld"]},
    "mjd": {"type":"float", "units":"days", "default":0.0,
            "description":"Modified Julian Date",
            "updater":lambda data: data["foc-mjd"]},
    "observing": {"type":"bool", "default":False,
                  "description":"Flag indicating if telescope is in 'measuring' state",
                  "updater":lambda data: bool(data["istmess"])},
    "scannum": {"type":"int", "default":0,
                "description":"Current scan number",
                "updater":lambda data: data["vscan"]},
    "subscannum" : {"type":"int", "default":0,
                    "description":"Current sub-scan number",
                    "updater":lambda data: data["vsubscan"]},
    "nsubscan" : {"type":"int", "default":1,
                  "description":"Number of sub-scans in current scan",
                  "updater":lambda data: data["vanzsubs"]},
    "time-remaining" : {"type":"float", "default":0.0, "units":"seconds",
                        "description":"Time remaining in current sub-scan",
                        "updater":lambda data: data["time-to-end"]},
    "time-elapsed" : {"type":"float", "default":0.0, "units":"seconds",
                      "description":"Time elapsed in current sub-scan",
                      "updater":lambda data: (data['mjuld'] - data['starttime'])*3600},
    "source-name" : {"type":"string", "default":"",
                     "description":"Current source name",
                     "updater":lambda data: data["fuelling"]},
    "azimuth" : {"type":"float", "default":0.0, "units":"degrees",
                 "description":"Current telescope azimuth",
                 "updater":lambda data: data["soll-1"]},
    "azimuth-offset" : {"type":"float", "default":0.0, "units":"degrees",
                        "description":"Difference between current and requested azimuth",
                        "updater":lambda data: data["soll-1"] - data['ist-1']},
    "azimuth-drive-speed" : {"type":"float", "default":0.0, "units":"deg/s",
                             "description":"Azimuth drive speed",
                             "updater":lambda data: data["vsoll-1"]/1200},
    "elevation" : {"type":"float", "default":0.0, "units":"degrees",
                   "description":"Current telescope elevation",
                   "updater":lambda data: data["soll-0"]},
    "elevation-offset" : {"type":"float", "default":0.0, "units":"degrees",
                          "description":"Difference between current and requested elevation",
                          "updater":lambda data: data["soll-0"] - data['ist-0']},
    "elevation-drive-speed" : {"type":"float", "default":0.0, "units":"deg/s",
                               "description":"Elevation drive speed",
                               "updater":lambda data: data["vsoll-0"]/1200},
    "ra" : {"type":"float", "default":0.0, "units":"degrees",
            "description":"Current Mean EQ2000 Right Ascension",
            "updater":lambda data: data["ra2000"]},
    "dec" : {"type":"float", "default":0.0, "units":"degrees",
             "description":"Current Mean EQ2000 Declination",
             "updater":lambda data: data["dk2000"]},
    "ra-1950" : {"type":"float", "default":0.0, "units":"degrees",
                 "description":"Current Mean EQ1950 Right Ascension",
                 "updater":lambda data: data["ra50"]},
    "dec-1950" : {"type":"float", "default":0.0, "units":"degrees",
                  "description":"Current Mean EQ1950 Declination",
                  "updater":lambda data: data["dk50"]},
    "glong" : {"type":"float", "default":0.0, "units":"degrees",
               "description":"Current Galactic longitude",
               "updater":lambda data: data["gallong"]},
    "glat" : {"type":"float", "default":0.0, "units":"degrees",
              "description":"Current Galactic latitude",
              "updater":lambda data: data["gallat"]},
    "elong" : {"type":"float", "default":0.0, "units":"degrees",
               "description":"Current Ecliptic longitude",
               "updater":lambda data: data["ekllong"]},
    "elat" : {"type":"float", "default":0.0, "units":"degrees",
              "description":"Current Ecliptic latitude",
              "updater":lambda data: data["ekllat"]},
    "frequency" : {"type":"float", "default":0.0, "units":"GHz",
                   "description":"Receiver frequency",
                   "updater":lambda data: data["fe-rxfrq"]},
    "receiver" : {"type":"string", "default":"",
                  "description":"The currently active receiver (wavelength.version)",
                  "updater":lambda data: str(data["wavelength"])},
    "focus" : {"type":"string", "default":"",
               "description":"Is the reciever at the primary or secondary focus?",
               "updater":lambda data: "primary" if data["foc-prim"] else "secondary"},
    "air-pressure" : {"type":"float", "default":0.0, "units":"hPa",
                      "description":"On site air pressure",
                      "range":[950,1050],
                      "updater":lambda data: data["vpressure"]},
    "humidity" : {"type":"float", "default":0.0, "units":"%",
                  "description":"On site humidity",
                  "range":[10,99],
                  "updater":lambda data: data["vhumidity"]},
    "air-temperature" : {"type":"float", "default":0.0, "units":"degrees C",
                         "description":"On site air temperature",
                         "range":[0,45],
                         "updater":lambda data: data["vtemperature"]},
    "wind-speed" : {"type":"float", "default":0.0, "units":"m/s",
                    "description":"On site wind speed",
                    "range":[0,10],
                    "updater":lambda data: data["vwindvel"]},
    "wind-direction" : {"type":"float", "default":0.0, "units":"degrees",
                        "description":"On site wind direction (0 degrees is North)",
                        "range":[0,360],
                        "updater":lambda data: data["delphin-7"]},
    "refraction-constant" : {"type":"float", "default":0.0, "units":"arcseconds",
                             "description":"On site refraction constant",
                             "range":[50,75],
                             "updater":lambda data: data["vrefract"]},
    "dew-point" : {"type":"float", "default":0.0, "units":"degrees C",
                   "description":"On site dew point",
                   "range":[1,45],
                   "updater":lambda data: data["delphin-5"]},
    "nula" : {"type":"float", "default":0.0, "units":"arcseconds",
              "description":"Azimtuth correction (?)",
              "updater":lambda data: data["vnula"]},
    "nule" : {"type":"float", "default":0.0, "units":"arcseconds",
              "description":"Elevation correction (?)",
              "updater":lambda data: data["vnule"]},
    "coll" : {"type":"float", "default":0.0, "units":"arcseconds",
              "description":"Receiver collimation",
              "updater":lambda data: data["vcoll"]},
    "x-lin" : {"type":"float", "default":0.0, "units":"",
               "description":"X-Linear",
               "updater":lambda data: data["foc-set-0"]/10.0},
    "y-lin" : {"type":"float", "default":0.0, "units":"",
               "description":"Y-Linear",
               "updater":lambda data: data["foc-set-1"]/10.0},
    "z-lin" : {"type":"float", "default":0.0, "units":"",
               "description":"Z-Linear",
               "updater":lambda data: data["foc-set-2"]/10.0},
    "x-rot" : {"type":"float", "default":0.0, "units":"arcminutes",
               "description":"X axis rotation",
               "updater":lambda data: data["foc-set-3"]/60.0},
    "y-rot" : {"type":"float", "default":0.0, "units":"arcminutes",
               "description":"Y axis rotation",
               "updater":lambda data: data["foc-set-4"]/60.0},
    "z-rot" : {"type":"float", "default":0.0, "units":"arcminutes",
               "description":"Z axis rotation",
               "updater":lambda data: data["foc-set-5"]/60.0},
    "pol-angle" : {"type":"float", "default":0.0, "units":"degrees",
                   "description":"Polarisation angle",
                   "updater":lambda data: data["foc-istpos-6"]},
    "project" : {"type":"string", "default":"",
                 "description":"Project ID",
                 "updater":lambda data: str(data["project"])}
    }