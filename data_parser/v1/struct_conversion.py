# import struct
# import collections

# from ..configuration import validate_config
# CONFIG = validate_config(version="v1")

from ..common.struct_conversion import (
    # endianness_struct_mapping,
    _DataFile,
    _Snippet
)




class DataFile(_DataFile):
    pass

class Snippet(_Snippet):

    def _convert_types(self, key, entry):
        if key == "Energy":
            # Reverse the Byte order
            return int.from_bytes(
                bytes([entry[2], entry[1], entry[0]])
            )
        else:
            return entry
