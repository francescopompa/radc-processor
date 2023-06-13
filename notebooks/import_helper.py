# Imports
import os
import sys
import pandas as pd
import matplotlib.pyplot as plt

path_to_data_parser = ".."
sys.path.append(path_to_data_parser)
from data_parser.configuration import CONFIG
from data_parser import struct_conversion, data_io, plotting


path_to_meas_interfaces = "../../nd-measurement-interfaces/"
sys.path.append(path_to_meas_interfaces)
from KeysightAgilent_3220A.pulse_emulation import pGen_pulse_class

# import(
#     get_total_pulse_width,
#     get_pulse_integral,
#     get_pulse_function,
#     get_pulse_integral_disc,
#     get_total_pulse_integral,
#     calculate_gap
# )

meas_base_path = "C:/Users/utrfh/WS22-23 (MA) Masterarbeit/Measurements"
irrelevant_labels = ["Type", "Subsecs", "Channel_number", "Rest", "min", "max", "trigger_count", "Multiplicity", "Trigger_info"]


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
        print(*i)
        # print(list(imports()))
