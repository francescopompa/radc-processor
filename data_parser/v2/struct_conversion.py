import os
import struct
import time

from ..configuration import validate_config
from ..common.struct_conversion import (
    endianness_struct_mapping,
    BaseDataFile,
    BaseSnippet
)
from udp_receiver.receiver_class import convert_bytes

CONFIG = validate_config(version="v2")

sizes = CONFIG["udp_package_structure"]


class DataFile(BaseDataFile):

    _contents = "events"

    def _calculate_format_string(self, endianness=None):
        if endianness is None:
            endianness = self._endianness
        endian = endianness_struct_mapping[endianness]

        fsm = CONFIG["struct_fields_mapping"]

        event_header = ''.join([
            value for value in fsm["Event_header"].values()
        ])

        snippet_header = ''.join([
            value for value in fsm["Snippet_header"].values()
        ])

        samples = f"{self.tracelength}{fsm['Sample']}"

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
        event_string = f"{endian} {event_header}"
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

        filesize = self.path.stat().st_size
        with open(self.path, "rb") as file:
            #
            # Todo: I suspect this line means holding the whole file in RAM,
            # which may be an issue with large files.
            #
            filecontents = file.read()

        _first_end = 1 + min(
            filesize,
            CONFIG["udp_package_structure"]["udp_package_size_bytes"]
            + event_struct.size
            )
        # offset = self.find_event_start(
        #     filecontents[:_first_end],
        #     event_struct
        #     )
        offset = 0

        while offset < filesize:
            try:
                event = Event(
                    tup=event_struct.unpack_from(filecontents, offset=offset),
                    snippet_length = snippet_struct.size,
                    snippet_size_bytes = self.snippet_size_bytes,
                    )
                offset += event_struct.size
            except (UnicodeDecodeError, ValueError, struct.error):
                # Sometimes, transmission is interrupted, causing "part 2" packages
                # to by scattered in the file, without preceding "part 1" event header
                offset += self.find_event_start(
                    filecontents[offset:offset+_first_end],
                    event_struct,
                    start = offset
                )
                continue

            snippets = event.header["Snippet_count"]
            for i in range(snippets):
                try:
                    _tup = snippet_struct.unpack_from(
                        filecontents,
                        offset=offset
                    )
                    
                    offset += snippet_struct.size
                    snippet = Snippet(_tup)
                    event.snippets.append(snippet)
                except ValueError:
                    print(f"Incorrect event header: event {event.header['Event_ID']}\n" 
                           f"offset {offset}.")
                    continue
                except struct.error as e:
                    print(f"Error unpacking snippet from {self.path.name}:")
                    print(" ", e)
                    print(f"Event {event.header['Event_ID']} aborted at offset {offset}.")
                    continue
                except:
                    continue
                        
                    


            # for i in range(event.stats["snippet_space"]):
            #     try:
            #         _tup=snippet_struct.unpack_from(
            #             filecontents,
            #             offset=offset+i*snippet_struct.size
            #             )
            #     except struct.error as e:
            #         print(f"Struct error while unpacking {self.path}", e)

            #     event.snippets.append(Snippet(_tup))

            # offset += event.stats["length"]
            yield event

    def find_event_start(self, bytesdata, event_struct, start=0):
        """
        Skips the first bytes until it can succesfully unpack an event.
        """
        #
        # Todo: currently this creates the same event twice and is inefficient
        # and does redundant try/except checks.
        # To clean up and merge into main loop above.
        #
        range_end = len(bytesdata)-event_struct.size
        if range_end <= 1:
            #
            # Todo: ugly solution to consume remaining end of file in case
            # it's missing something
            #
            return 1

        for i in range(1,range_end):
            _tup = event_struct.unpack_from(bytesdata, offset=i)

            try:
                e = Event(tup=_tup)
                break
            # except* (struct.error, UnicodeDecodeError):   # Python 3.11 way
            except (struct.error, UnicodeDecodeError, ValueError):
                continue
        else:
            self.skipped_bytes.append((start, start, 0))
        #     raise RuntimeError(
        #         f"Could not find next event in {self.path.name} within "
        #         f"the bytes {start} to {start+i}."
        #         )

        if i > 0:
            self.skipped_bytes_total += i
            self.skipped_bytes.append((start, start+i, i))
            # print(f"Struct conversion dropped Bytes {start} to {start+i} "
            #       f"from file {self.path.name}.")
        return i


    def unpack(self):
        self.events = list(self._unpack_events())
        if self.skipped_bytes_total > 0:
            print(
            f"Unpacking from {self.path.name} skipped {convert_bytes(self.skipped_bytes_total)}",
            
            f"out of {convert_bytes(self.path.stat().st_size)} in total. ({self.skipped_bytes_total/self.path.stat().st_size:.2%})\n"
            # self.skipped_bytes
            )
        return self.skipped_bytes

    def get_records(self):
        if len(self.events) == 0:
            self.unpack()

        for event in self.events:
            yield event.get_record()


class Event(BaseSnippet):

    _kwargs = {
        "snippet_length": 64,
        "snippet_size_bytes": (14, 136),
        }
    _contents = "snippets"
    _include_UDP_header_default = False
    _mapping_dict = CONFIG["struct_fields_mapping"]
    _mapping_name = "Event_header"
    _stats_default = {
        "length": (
            sizes["event_header_size_bytes"]
            + sizes["snippet_header_size_bytes"]
            + sizes["default_trace_length"]*sizes["sample_size_bytes"]
        ),
        "snippet_space": 0
        }

    def _init_contents_with_tuple(self, tup, index):
        setattr(self, self._contents, [])

    def _check_integrity(self):
        return (self.header["Trigger_type"] == 'E'
                and self.header['Snippet_count'] in range(1,100)
                and self.header["Timestamp_s"] < time.time()
                and self.header["Timestamp_s"] > 1699000000

                )
        # return True




    def _convert_types(self, key, entry):
        match key:
            case "Type"|"Trigger_type":
                return entry.decode("ascii")

            case "Event_ID":
                # Reverse the Byte order
                return int.from_bytes(
                    entry[::-1], "big"
                    # bytes([entry[2], entry[1], entry[0]])
                )
            case _:
                return entry

    def _calculate_stats(self):
        self.stats["length"] = (
            sizes["event_header_size_bytes"]
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
            **self.header,
            **self.stats,
            "snippets": [
                snippet.get_record() for snippet in self.snippets
            ]
        }





class Snippet(BaseSnippet):
    # Channel_number: "B"  # 1 Byte unsigned char integer
    # Energy: "3s"     # 3 Bytes arbitrary char
    # Timedelta_samples: "h"  # 2 Byte signed int ("short")
    # Snippet_number: "B" # 1 Byte unsigned int
    # Info_flags: "c" # 1 Byte bits
    _include_UDP_header_default = False

    pass