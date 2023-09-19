"""
Package data_parser

Package written to extract measured data out of collected data-files and
convert it to a pandas DataFrame storeable to disk, as well as to
generate and handle plots out of the data sets.

Usage: Tbd.
"""

# from .configuration import CONFIG
import .struct_conversion as struct_conversion
import .data_io
import .plotting

#
# Todo:
# - [ ] Call init() from __init__
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

    pdf = data_io.make_total_dataFrame([df])

    plotting.plot_rows(pdf.iloc[0])
    # plotting.plot_rows(pdf)




if __name__ == "__main__":
    main()