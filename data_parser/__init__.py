"""
Library for unpacking of binary data-files captured from the RADC-40 board
with udp_receiver into pandas DataFrames.
Can be extended to other file structures and formats.

The library includes two conversion schemes:
- v1: is adequate for the old data-structure from the RADC firmware V1.X
    which uses simple snippets (one per pulse, each channel triggers independently).
- v2: is adequate for the new data-structure from the RADC firmware V2.X
    which uses event frames containing up to 4 snippets each and additional
    context data like sum-channel trigger information.

Usage of the conversion requires initialization of the library with the desired
version:

    import data_parser
    data_parser.init("vX")  # v1 or 1, v2 or 2, default is "v1"

    from data_parser import struct_conversion

Additionally this library provides:
- data_io: helper functions to convert data-files to pandas DataFrames
    (requires `struct_conversion` initialization).
- dataFrame_helpers: helper functions for common information or manipulation
    calls about generated DataFrames.
- plotting: functions to generate plots out of generated DataFrames.
"""
# from . import data_io, dataFrame_helpers, plotting

VERSION = None
"""Integer variable holding the current converter version. Initialized with `None`."""
VERSION_STR = ""
"""String representation of the current converter version ("vX")."""

VERSIONS = [None, "v1", "v2"]
"""List of possible converter versions."""

DEFAULT_VERSION = "v1"
"""Default converter version value."""

# __all__ = [
#         "data_io",
#         "dataFrame_helpers",
#         "plotting",
#         "struct_conversion",
#     ]

def init(_VERSION=DEFAULT_VERSION):
    """
    Initialization function for this library.
    `struct_conversion` implicitely loads the correct version of the unpacking
    algorithm in accordance with the global variables defined in this module.
    This function sets those variables and is required to use this library.

    Default is "v1".
    """
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

