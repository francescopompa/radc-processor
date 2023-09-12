
# from . import data_io, dataFrame_helpers, plotting

VERSION = None
VERSION_STR = ""

VERSIONS = [None, "v1", "v2"]

DEFAULT_VERSION = "v1"

__all__ = [
        "data_io",
        "dataFrame_helpers",
        "plotting",
        "struct_conversion",
    ]

def init(_VERSION=DEFAULT_VERSION):
    global VERSION, VERSION_STR
    if VERSION is not None:
        return

    match _VERSION:
        case 1|"v1"|None:
            VERSION = 1
            VERSION_STR = "v1"
        case 2|"v2":
            VERSION = 2
            VERSION_STR = "v2"

