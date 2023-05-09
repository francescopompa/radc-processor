import struct
import collections

from .configuration import CONFIG

field_struct_mapping = collections.OrderedDict({
    # UDP Header
    "UDP_Type": "c",    # 1 Byte char
    "UDP_Number": "B",  # 1 Byte unsigned char
    "UDP_Rest": "2s",   # 2 Bytes char

    # RADC Header for each snippet
    "Snippet_Channel_number": "B",  # 1 Byte unsigned char integer
    "Snippet_Trigger_info": "B",    # 1 Byte unsigned char integer
    "Snippet_Event_ID": "H",    # 2 Bytes unsigned short integer
    "Snippet_Energy": "3s",     # 3 Bytes arbitrary char
    "Snippet_Multiplicity": "B",  # 1 Byte unsigned char integer
    "Snippet_Subsecs": "I",     # 4 Bytes unsigned integer
    "Snippet_Seconds": "I",     # 4 Bytes unsigned integer

    # RADC single sample
    "Sample": "h",      # 2 Bytes short integer
})

endianness_struct_mapping = {
    # SOURCE: https://docs.python.org/3/library/struct.html#format-strings
    "native": "@",
    "native_standardized": "=",
    "little-endian": "<",
    "big-endian": ">",
    "network": "@",  # (big endian)
}


class DataFile():

    def __init__(self,
                 path,
                 tracelength=CONFIG["udp_package_structure"]["default_trace_length"],
                 endianness="little-endian"
                 ) -> None:
        self.path = path
        self.tracelength = tracelength
        self.snippets = []  # iter(())
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
            fsm["UDP_header"][key] for key in fsm["UDP_header"].keys()
        ])

        snippet_header = ''.join([
            fsm["Snippet_header"][key] for key in fsm["Snippet_header"].keys()
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
            return iter(Snippet(structs))

        for istruct in structs:
            yield Snippet(istruct)

    def get_records(self):
        if len(self.snippets) == 0:
            self.unpack()

        for snippet in self.snippets:
            yield snippet.get_record()


class Snippet():

    def __init__(self, tuple) -> None:
        self.udp_header = {}
        self.header = {}
        self.samples = []
        self.trigger_IDs = []

        self.stats = {
            "min": 0,
            "max": 0,
            "trigger_count": 0,
        }

        self.__init_with_tuple(tuple)
        self.__calculate_stats()


    def __init_with_tuple(self, tuple):
        for i,key in enumerate(CONFIG["struct_fields_mapping"]["UDP_header"], 0):
            self.udp_header[key] = tuple[i]

        # Use previous counter as offset:
        for i,key in enumerate(CONFIG["struct_fields_mapping"]["Snippet_header"], i+1):
            self.header[key] = self.__convert_types(key, tuple[i])

        self.samples = list(self.__convert_samples(tuple[i+1:]))

    def __convert_types(self, key, entry):
        if key == "Energy":
            # Reverse the Byte order
            return int.from_bytes(
                bytes([entry[2], entry[1], entry[0]])
                )
        else:
            return entry

    def __convert_samples(self, tuple):
        for id, sample in enumerate(tuple):
            # SOURCE https://realpython.com/python-bitwise-operators/#bitmasks
            t = bool((sample >> 15) & 1) # Trigger flag
            i = bool((sample >> 14) & 1) # Inhibit flag
            unsigned_val = sample & 0b0011111111111111  # 16 bits incl. 14 ones.
            s = unsigned_val >> 13  # 1: negative, 0:positive

            if (t and not i):
                # Real trigger case that wasn't inhibited:
                self.trigger_IDs.append(id)

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
