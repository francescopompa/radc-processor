import struct
import collections

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


class _DataFile():

    _contents = "snippets"

    def __init__(self,
                 path,
                 tracelength=CONFIG["udp_package_structure"]["default_trace_length"],
                 endianness="little-endian"
                 ) -> None:
        self.path = path
        self.tracelength = tracelength
        setattr(self, self._contents, [])
        # self.snippets = []  # iter(())
        self.snippet_size_bytes = None

        self.__endianness = endianness
        self.format = self.__calculate_format_string(self.__endianness)

    def __validate_format_string(self, string, size):
        if struct.calcsize(string) != size:
            raise ValueError(
                f"Struct Format string \"{string}\" does not match size {size} bytes.")

    def __calculate_format_string(self, endianness=None):
        if endianness is None:
            endianness = self.__endianness

        fsm = CONFIG["struct_fields_mapping"]
        package_header = ''.join([
            value for value in fsm["UDP_header"].values()
        ])

        snippet_header = ''.join([
            value for value in fsm["Snippet_header"].values()
        ])

        samples = self.tracelength * fsm["Sample"]

        self.__validate_format_string(
            package_header, CONFIG["udp_package_structure"]["udp_header_size_bytes"])
        self.__validate_format_string(
            snippet_header, CONFIG["udp_package_structure"]["snippet_header_size_bytes"])
        self.__validate_format_string(
            fsm["Sample"], CONFIG["udp_package_structure"]["sample_size_bytes"])

        string = f"{endianness_struct_mapping[endianness]} {package_header} {snippet_header} {samples}"

        self.snippet_size_bytes = struct.calcsize(string)

        return string

    def unpack(self):
        with open(self.path, "rb") as file:
            filecontents = file.read()

        structs = struct.iter_unpack(self.format, filecontents)
        self.snippets = list(self.__convert_struct_to_snippet(structs))

    def __convert_struct_to_snippet(self, structs):
        if not isinstance(structs, collections.abc.Iterable):
            return iter(_Snippet(structs))

        for istruct in structs:
            yield _Snippet(istruct)

    def get_records(self):
        if len(self.snippets) == 0:
            self.unpack()

        for snippet in self.snippets:
            yield snippet.get_record()


class _Snippet():

    _kwargs = []
    _contents = "samples"
    _mapping_dict = CONFIG["struct_fields_mapping"]
    _stats_default = {
            "min": 0,
            "max": 0,
            "trigger_count": 0,
        }

    def __init__(self, tup, **kwargs) -> None:
        self.udp_header = {}
        self.header = {}
        # self.samples = []
        self.trigger_IDs = []

        self.stats = self._stats_default.copy()

        for key, val in kwargs.items():
            if key in self._kwargs:
                setattr(self, key, val)

        index = self.__init_header_with_tuple(tup)
        self.__init_contents_with_tuple(tup, index)
        self.__calculate_stats()

    def __init_header_with_tuple(self, tup):
        # if ["UDP_header"] is empty, i is not declared. Set to -1 as backup
        i = -1

        for i, key in enumerate(self._mapping_dict["UDP_header"], 0):
            self.udp_header[key] = tup[i]

        # Use previous counter (or -1) as offset:
        for i, key in enumerate(self._mapping_dict["Snippet_header"], i+1):
            self.header[key] = self.__convert_types(key, tup[i])

        if all(key in self.header for key in ["Seconds", "Subsecs"]):
            self.header["Timestamp_s"] = self.__convert_time(
                self.header["Seconds"],
                self.header["Subsecs"],
            )

        return i+1

    def __init_contents_with_tuple(self, tup, index):
        setattr(self, self._contents, list(self.__convert_samples(tup[index:])))


    def __convert_types(self, key, entry):
        match key:
            case "Type":
                return entry.decode("ascii")
            case "Energy":
                # Reverse the Byte order
                return int.from_bytes(
                    bytes([entry[2], entry[1], entry[0]])
                )
            case _:
                return entry

    def __convert_time(self, seconds, subsecs, freq=62500000):
        return seconds+subsecs/freq # divide by the clock frequency


    def __convert_samples(self, tup):
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

    def __calculate_stats(self):
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
