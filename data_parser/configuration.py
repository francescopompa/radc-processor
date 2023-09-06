
import os
import time
import yaml
from pathlib import Path

from . import VERSION, init
if VERSION is None:
    init()
from . import VERSION_STR

path_map = {
    "radc-processor": f"data_parser/{VERSION_STR}/{VERSION_STR}.configuration.yaml",
    "notebooks": f"../data_parser/{VERSION_STR}/{VERSION_STR}.configuration.yaml",
    "data_parser": f"{VERSION_STR}.configuration.yaml",
    "else": Path(
        r"C:\Users\utrfh\WS22-23 (MA) Masterarbeit\Codes\radc-processor\data_parser",
        VERSION_STR,
        f"{VERSION_STR}.configuration.yaml"
    )
}
try:
    config_path = path_map[os.getcwd().split('\\')[-1].split('/')[-1]]
except KeyError:
    config_path = path_map["else"]


with open(config_path, "r", encoding="utf-8") as file:
    CONFIG = yaml.safe_load(file)


def _insert_variable_value(string=""):
    string = string.lstrip("$").lower()

    if string == "date":
        return time.strftime("%Y-%m-%d")


def _loop_through_dict(config, dpath=None):
    if dpath is None:
        dpath = config

    for key, value in config.items():
        if isinstance(value, dict):
            _loop_through_dict(value, dpath=dpath[key])
        elif isinstance(value, str) and value.startswith("$"):
            dpath[key] = _insert_variable_value(value)


def validate_config():
    # global CONFIG
    _loop_through_dict(CONFIG)

validate_config()

print("Loaded CONFIG", CONFIG)
