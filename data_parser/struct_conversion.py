from . import VERSION, VERSION_STR

match VERSION:
    #
    # Todo: Check what happens on re-import after second call to init()
    #
    case 1:
        from .v1.struct_conversion import *
    case 2:
        from .v2.struct_conversion import *
    case None:
        raise ImportError(f"Module data_parser is not initialized: VERSION={VERSION}. Please call data_parser.init(VERSION)")

print(f"Imported struct_conversion {VERSION_STR}")