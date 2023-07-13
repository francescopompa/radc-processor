# Imports
import os
import sys
import pandas as pd
import matplotlib.pyplot as plt

def pjoin(path):
    return os.path.join(
        os.path.dirname(__file__),
        path
    )

path_to_data_parser = pjoin("..")
sys.path.append(path_to_data_parser)
from data_parser.configuration import CONFIG
from data_parser import struct_conversion, data_io, plotting
from measurement_class import Measurement

path_to_meas_interfaces = pjoin("../../nd-measurement-interfaces/")
sys.path.append(path_to_meas_interfaces)
from KeysightAgilent_3220A.pulse_emulation import pGen_pulse_class

from KeysightAgilent_3220A import Agilent3220A, pulse_emulation
from Tektronix_DPO4104B import TektronixDPO4104B

import pyvisa
from pyvisa.errors import VisaIOError

# import(
#     get_total_pulse_width,
#     get_pulse_integral,
#     get_pulse_function,
#     get_pulse_integral_disc,
#     get_total_pulse_integral,
#     calculate_gap
# )

import scipy
import scipy.signal as scp

meas_base_path = pjoin(Measurement.base_path)
irrelevant_labels = ["Type", "Subsecs", "Channel_number", "Rest", "min", "max", "trigger_count", "Multiplicity", "Trigger_info"]


def hold(message=""):
    if message != "" and not message.endswith(" "):
        message += " "
    uinput = input(f"{message}Press [ENTER] to continue.")
    if uinput in ["\n", ""]:
        return uinput
    else:
        hold(message)


import json
import numpy as np
class CustomEncoder(json.JSONEncoder):
    """ Special json encoder for numpy types """
    def default(self, obj):
        if isinstance(obj, (np.int_, np.intc, np.intp, np.int8,
                            np.int16, np.int32, np.int64, np.uint8,
                            np.uint16, np.uint32, np.uint64)):
            return int(obj)
        elif isinstance(obj, (np.float_, np.float16, np.float32,
                              np.float64)):
            return float(obj)
        elif isinstance(obj, (np.ndarray,)):
            return obj.tolist()
        return json.JSONEncoder.default(self, obj)




# ----------------------------------------------------------------------
import types
def imports():
    for name, val in sorted(globals().items()):
        if name.startswith("_"):
            continue
        if isinstance(val, types.ModuleType):
            yield name, val.__name__
        elif isinstance(val, str) or isinstance(val, list):
            yield name, val

def list_imports():
    for i in imports():
        print(i[0], f"\t{i[1:]}")
        # print(list(imports()))
