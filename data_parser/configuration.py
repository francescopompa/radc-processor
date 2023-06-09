
import os
import time
import yaml

path_map = {
    "radc-processor": "data_parser/configuration.yaml",
    "notebooks": "../data_parser/configuration.yaml",
    "data_parser": "configuration.yaml",
}
config_path = path_map[os.getcwd().split('\\')[-1].split('/')[-1]]

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
