
import os
import time
import yaml

path_map = {
    "radc_processor": "data_parser/configuration.yml",
    "data_parser": "configuration.yml",
}
config_path = path_map[os.getcwd().split('\\')[-1].split('/')[-1]]

with open(config_path, "r") as file:
    CONFIG = yaml.safe_load(file)


def _insert_variable_value(string=""):
    string = string.lstrip("$").lower()

    if string == "date":
        return time.strftime("%Y-%m-%d")


def _loop_through_dict(CONFIG, dpath=None):
    if dpath is None:
        dpath = CONFIG

    for key, value in CONFIG.items():
        if isinstance(value, dict):
            _loop_through_dict(value, dpath=dpath[key])
        elif isinstance(value, str) and value.startswith("$"):
                dpath[key] = _insert_variable_value(value)


def validate_config():
    global CONFIG
    _loop_through_dict(CONFIG)

validate_config()

print(CONFIG)
