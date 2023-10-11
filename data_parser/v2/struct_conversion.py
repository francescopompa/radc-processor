import os
import struct
# import collections

from ..configuration import validate_config
CONFIG = validate_config(version="v2")

from ..common.struct_conversion import (
    endianness_struct_mapping,
    _DataFile,
    _Snippet
)

sizes = CONFIG["udp_package_structure"]


class DataFile(_DataFile):

    _contents = "events"

    def _calculate_format_string(self, endianness=None, include_UDP_header=None):
        if endianness is None:
            endianness = self.__endianness
        if include_UDP_header is None:
            include_UDP_header = self.include_UDP_header
        endian = endianness_struct_mapping[endianness]

        fsm = CONFIG["struct_fields_mapping"]

        if include_UDP_header is True:
            package_header = ''.join([
                value for value in fsm["UDP_header"].values()
            ])
            self._validate_format_string(
                package_header,
                CONFIG["udp_package_structure"]["udp_header_size_bytes"],
                structname="package_header"
            )
        else:
            package_header = ""


        event_header = ''.join([
            value for value in fsm["Event_header"].values()
        ])

        snippet_header = ''.join([
            value for value in fsm["Snippet_header"].values()
        ])

        samples = self.tracelength * fsm["Sample"]

        self._validate_format_string(
            event_header,
            CONFIG["udp_package_structure"]["event_header_size_bytes"],
            structname="event_header")
        self._validate_format_string(
            snippet_header,
            CONFIG["udp_package_structure"]["snippet_header_size_bytes"],
            structname="snippet_header")
        self._validate_format_string(
            fsm["Sample"],
            CONFIG["udp_package_structure"]["sample_size_bytes"],
            structname="sample")

        # string = f"{endian} {package_header} {snippet_header} {samples}"
        event_string = f"{endian} {package_header} {event_header}"
        snippet_string = f"{endian} {snippet_header} {samples}"

        self.snippet_size_bytes = (
            struct.calcsize(event_string),
            struct.calcsize(snippet_string)
            )

        return event_string, snippet_string


    def _unpack_events(self):
        event_string, snippet_string = self.format
        event_struct = struct.Struct(event_string)
        snippet_struct = struct.Struct(snippet_string)

        offset = 0
        filesize = os.stat(self.path).st_size
        with open(self.path, "rb") as file:
            filecontents = file.read()
        while offset < filesize:
            event = Event(
                tup=event_struct.unpack_from(filecontents, offset=offset),
                snippet_length = snippet_struct.size,
                snippet_size_bytes = self.snippet_size_bytes,
                include_UDP_header = self.include_UDP_header
                )

            for i in range(event.stats["snippet_space"]):
                event.snippets.append(Snippet(
                    tup=snippet_struct.unpack_from(
                        filecontents,
                        offset=offset+i*snippet_struct.size
                        ),
                    include_UDP_header=self.include_UDP_header
                ))

            offset += event.stats["length"]
            yield event


    def unpack(self):
        self.events = list(self._unpack_events())

    def get_records(self):
        if len(self.events) == 0:
            self.unpack()

        for event in self.events:
            yield event.get_record()


class Event(_Snippet):

    _kwargs = ["snippet_length", "snippet_size_bytes"]
    _contents = "snippets"
    _mapping_dict = CONFIG["struct_fields_mapping"]
    _mapping_name = "Event_header"
    _stats_default = {
        "length": (
            sizes["udp_header_size_bytes"]
            + sizes["event_header_size_bytes"]
            + sizes["snippet_header_size_bytes"]
            + sizes["default_trace_length"]*sizes["sample_size_bytes"]
        ),
        "snippet_space": 0
        }

    def _init_contents_with_tuple(self, tup, index):
        setattr(self, self._contents, [])

    def _convert_types(self, key, entry):
        match key:
            case "Type"|"Trigger_type":
                return entry.decode("ascii")
            case "Event_ID":
                # Reverse the Byte order
                return int.from_bytes(
                    bytes([entry[2], entry[1], entry[0]])
                )
            case _:
                return entry

    def _calculate_stats(self):
        self.stats["length"] = (
            sizes["udp_header_size_bytes"] if self.include_UDP_header is True else 0
            + sizes["event_header_size_bytes"]
            + self.header["Snippet_count"]
                * self.snippet_length
            )
        self.stats["snippet_space"] = (
            min(
                self.header["Snippet_count"],
                ((sizes["udp_package_size_bytes"]
                  - self.snippet_size_bytes[0])
                // self.snippet_size_bytes[1])
            )
        )

    def get_record(self):
        return {
            **self.udp_header,
            **self.header,
            **self.stats,
            "snippets": [
                snippet.get_record() for snippet in self.snippets
            ]
        }





class Snippet(_Snippet):
    # Channel_number: "B"  # 1 Byte unsigned char integer
    # Energy: "3s"     # 3 Bytes arbitrary char
    # Timedelta_samples: "h"  # 2 Byte signed int ("short")
    # Snippet_number: "B" # 1 Byte unsigned int
    # Info_flags: "c" # 1 Byte bits
    pass