
# from . import data_io, dataFrame_helpers, plotting

VERSION = None
VERSION_STR = ""

VERSIONS = [None, "v1", "v2"]

DEFAULT_VERSION = "v1"

def init(_VERSION=DEFAULT_VERSION):
    global VERSION, VERSION_STR

    match _VERSION:
        case 1|"v1"|None:
            from .v1 import (
            struct_conversion,
            )
            VERSION = 1
            VERSION_STR = "v1"
        case 2|"v2":
            from .v2 import (
            struct_conversion,
            )
            VERSION = 2
            VERSION_STR = "v2"

    from . import data_io, dataFrame_helpers, plotting

    global __all__
    __all__ = [
        "data_io",
        "dataFrame_helpers",
        "plotting",
        "struct_conversion",
    ]

