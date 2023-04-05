

from configuration import CONFIG
import struct_conversion
import data_io
#
# Todo:
# - [ ] Define folders to load
# - [ ] Define files to load
# - [ ] Convert to DataFrame
# - [ ] define Plot functions for sample, snippet, df-Entry
# - [ ] define Plot functions for events, including multi-channel plot
# - [ ] define plot saving
# - [ ] define df saving/loading
# - [ ] any additional statistics
# - [ ] implement logger
# - [ ] share config file with commander?
# - [ ] share config loading module with commander?
# - [ ] command-line arguments
# - [ ] load/write/update dir-info file for datamanager?
# - [ ] Decide if should switch to Root Trees... https://root.cern/manual/trees/


def main():
    df = struct_conversion.DataFile(
        r"C:\Users\utrfh\WS22-23 (MA) Masterarbeit\RADC_testData\2023-03-20_UdpReceiverClass_tests\radc.4.bin"
        )

    pdf = data_io.total_dataFrame([df])



if __name__ == "__main__":
    main()