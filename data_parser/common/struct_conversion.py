import struct
from pathlib import Path

from ..configuration import CONFIG

# field_struct_mapping = collections.OrderedDict({
#     # UDP Header
#     "UDP_Type": "c",    # 1 Byte char
#     "UDP_Number": "B",  # 1 Byte unsigned char
#     "UDP_Rest": "2s",   # 2 Bytes char

#     # RADC Header for each snippet
#     "Snippet_Channel_number": "B",  # 1 Byte unsigned char integer
#     "Snippet_Trigger_info": "B",    # 1 Byte unsigned char integer
#     "Snippet_Event_ID": "H",    # 2 Bytes unsigned short integer
#     "Snippet_Energy": "3s",     # 3 Bytes arbitrary char
#     "Snippet_Multiplicity": "B",  # 1 Byte unsigned char integer
#     "Snippet_Subsecs": "I",     # 4 Bytes unsigned integer
#     "Snippet_Seconds": "I",     # 4 Bytes unsigned integer

#     # RADC single sample
#     "Sample": "h",      # 2 Bytes short integer
# })

endianness_struct_mapping = {
    # SOURCE: https://docs.python.org/3/library/struct.html#format-strings
    "native": "@",
    "native_standardized": "=",
    "little-endian": "<",
    "big-endian": ">",
    "network": "@",  # (big endian)
}


class BaseDataFile():
    """
    The base class for DataFile objects.
    This class is initialized with a path and provides methods to unpack
    data from this path.
    Unpacking and storing data in the correct hierarchy and fields is handled
    implicitely.
    """

    _contents = None
    """A string describing the kind of object this class holds."""

    def __init__(self,
                 path,
                 tracelength=CONFIG["udp_package_structure"]["default_trace_length"],
                 endianness="little-endian",
                 include_UDP_header=False,
                 ) -> None:
        self.path = Path(path)
        self.tracelength = tracelength
        self.include_UDP_header = include_UDP_header
        setattr(self, self._contents, [])
        # self.snippets = []  # iter(())

        self.skipped_bytes = []
        self.skipped_bytes_total = 0

        self.snippet_size_bytes = None

        self._endianness = endianness
        self.format = self._calculate_format_string()

    def _validate_format_string(self, string, size, structname=""):
        if not any(
            string.startswith(e) for e in endianness_struct_mapping.values()
            ):
            string = endianness_struct_mapping[self._endianness] + string
        structname += " " if structname else ""

        calcsize = struct.calcsize(string)
        if calcsize != size:
            raise ValueError(
                f"{self.__class__.__name__}: {structname}struct Format string \"{string}\" of size {calcsize} does not match size {size} bytes.")


    def _calculate_format_string(self, endianness=None, include_UDP_header=None):
        """
        Method to generate the unpacking-format-descriptor for the struct package.
        """
        raise NotImplementedError

    def unpack(self):
        """
        This method starts the unpacking of the file into one single hierarchical
        dictionnary containing all header and signal data.
        """
        raise NotImplementedError

    def get_records(self):
        """
        Method returning a generator used by pandas to create a DataFrame from.
        """
        raise NotImplementedError



class BaseSnippet():

    _kwargs = {}
    _contents = "samples"
    _include_UDP_header_default = True
    _mapping_dict = CONFIG["struct_fields_mapping"]
    _mapping_name = "Snippet_header"
    _stats_default = {
            "min": 0,
            "max": 0,
            "trigger_count": 0,
        }

    def __init__(self, tup, include_UDP_header=None, **kwargs) -> None:
        """
        Within __init__, `self` will always match the baseclass/superclass.
        Name mangling (__method_name()) should therefore not be used for
        methods the subclasses want to overwrite.
        """
        self.udp_header = {}
        self.header = {}
        # self.samples = []
        self.trigger_IDs = []
        self.include_UDP_header = include_UDP_header or self._include_UDP_header_default

        self.stats = self._stats_default.copy()

        for key, default in self._kwargs.items():
            setattr(self, key, kwargs.pop(key, default))

        index = self._init_header_with_tuple(tup)
        self._init_contents_with_tuple(tup, index)
        # self._calculate_stats() 

    def _init_header_with_tuple(self, tup):
        #
        # Implement event unpacking
        #
        # print(tup)
        # if ["UDP_header"] is empty, i is not declared. Set to -1 as backup
        i = -1

        if self.include_UDP_header is True:
            for i, key in enumerate(self._mapping_dict["UDP_header"], 0):
                self.udp_header[key] = tup[i]
            # print(self.udp_header, self.include_UDP_header)

        # Use previous counter (or -1) as offset:
        for i, key in enumerate(self._mapping_dict[self._mapping_name], i+1):
            self.header[key] = self._convert_types(key, tup[i])

        if all(key in self.header for key in ["Seconds", "Subsecs"]):
            self.header["Timestamp_s"] = self._convert_time(
                self.header["Seconds"],
                self.header["Subsecs"],
            )

        if not self._check_integrity():
            raise ValueError(f"Wrong values for snippet in header {self.header}")

        return i+1

    def _init_contents_with_tuple(self, tup, index):
        setattr(self, self._contents, list(self._convert_samples(tup[index:])))


    def _check_integrity(self):
        # return (self.header['Channel_number'] in range(36) 
        #         and self.header['Snippet_number'] in range(1,30)
        #         and (int(self.header['Info_flags']) == 0 or int(self.header['Info_flags']) == 1)
        #         and 0 < self.header['Energy'] < 50000 
        #         )
        return True
                

    def _convert_types(self, key, entry):
        match key:
            case "Type"|'Trigger_type':
                return entry.decode("ascii")
            case "Energy":
                # Reverse the Byte order
                return int.from_bytes(
                    bytes([entry[2], entry[1], entry[0]]), "big"
                )
            case 'Info_flags':
                return int.from_bytes(entry,'big')
            case _:
                return entry

    def _convert_time(self, seconds, subsecs, freq=62500000):
        return seconds+subsecs/freq # divide by the clock frequency


    def _convert_samples(self, tup):
        for ID, sample in enumerate(tup):
            # SOURCE https://realpython.com/python-bitwise-operators/#bitmasks
            t = bool((sample >> 15) & 1)  # Trigger flag
            i = bool((sample >> 14) & 1)  # Inhibit flag
            # 16 bits incl. 14 ones.
            unsigned_val = sample & 0b0011111111111111
            s = unsigned_val >> 13  # 1: negative, 0:positive

            if (t and not i):
                # Real trigger case that wasn't inhibited:
                self.trigger_IDs.append(ID)

            # Considering the ADC to use two's-complement signed values
            yield -s*2**14 + unsigned_val

            # yield {
            #     # "total": bin(sample),
            #     "trigger": ,
            #     "value": value,
            # }

    def _calculate_stats(self):
        self.stats["min"] = min(self.samples)
        self.stats["max"] = max(self.samples)
        self.stats["trigger_count"] = len(self.trigger_IDs)

    def get_record(self):
        return {
            **self.udp_header,
            **self.header,
            **self.stats,
            "trigger_IDs": self.trigger_IDs,
            "samples": self.samples
        }
