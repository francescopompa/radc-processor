import struct
import collections

from ..configuration import validate_config
from ..common.struct_conversion import (
    endianness_struct_mapping,
    BaseDataFile,
    BaseSnippet
)

CONFIG = validate_config(version="v1")



class DataFile(BaseDataFile):

    _contents = "snippets"

    def _calculate_format_string(self, endianness=None, include_UDP_header=None):
        if endianness is None:
            endianness = self.__endianness
        if include_UDP_header is None:
            include_UDP_header = self.include_UDP_header

        fsm = CONFIG["struct_fields_mapping"]

        if include_UDP_header is True:
            package_header = ''.join([
                value for value in fsm["UDP_header"].values()
            ])
            self._validate_format_string(
                package_header, CONFIG["udp_package_structure"]["udp_header_size_bytes"]
            )
        else:
            package_header = ""

        snippet_header = ''.join([
            value for value in fsm["Snippet_header"].values()
        ])

        samples = f"{self.tracelength}{fsm['Sample']}"

        self._validate_format_string(
            snippet_header, CONFIG["udp_package_structure"]["snippet_header_size_bytes"])
        self._validate_format_string(
            fsm["Sample"], CONFIG["udp_package_structure"]["sample_size_bytes"])

        string = f"{endianness_struct_mapping[endianness]} {package_header} {snippet_header} {samples}"

        self.snippet_size_bytes = struct.calcsize(string)

        return string

    def _convert_struct_to_snippet(self, structs):
        if not isinstance(structs, collections.abc.Iterable):
            return iter(Snippet(structs, include_UDP_header=self.include_UDP_header))

        for istruct in structs:
            yield Snippet(istruct, include_UDP_header=self.include_UDP_header)

    def unpack(self):
        with open(self.path, "rb") as file:
            filecontents = file.read()

        structs = struct.iter_unpack(self.format, filecontents)
        self.snippets = list(self._convert_struct_to_snippet(structs))

    def get_records(self):
        if len(self.snippets) == 0:
            self.unpack()

        for snippet in self.snippets:
            yield snippet.get_record()



class Snippet(BaseSnippet):

    def _convert_types(self, key, entry):
        if key == "Energy":
            # Reverse the Byte order
            return int.from_bytes(
                bytes([entry[2], entry[1], entry[0]])
            )
        else:
            return entry
