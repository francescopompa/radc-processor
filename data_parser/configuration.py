
import os
import time
import yaml
from pathlib import Path

from . import VERSION, init
if VERSION is None:
    init()
from . import VERSION_STR


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


def validate_config(version: str = VERSION_STR):

    config_path = Path(
        __file__,
        "..",
        version,
        f"{version}.configuration.yaml"
        ).resolve()

    with open(config_path, "r", encoding="utf-8") as file:
        CONFIG = yaml.safe_load(file)

    _loop_through_dict(CONFIG)
    CONFIG["VERSION"] = VERSION

    return CONFIG

CONFIG = validate_config()

# print("Loaded CONFIG", CONFIG)
