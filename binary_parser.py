
import os
import struct
import json

testfolder = r"U:\WS22-23 (MA) Masterarbeit\RADC_testData"
subfolder = "2023-01-20_UDP"
testfile_bin = "test.bin" # len(filecontents): 11 597 140 Bytes = 8167 * 1420
testfile_wfm = "ND00000000.wfm"

testfolder = r"U:\WS22-23 (MA) Masterarbeit\RADC_testData"
subfolder = "2023-01-10_PulsTrigger"
testfile_bin = "radc_nd.bin" # len(filecontents):
testfile_bin = "radc.bin.3" # len(filecontents):


# Format of a single UDP-Package:
RADC_HEADER_SIZE = 16
RADC_PKG_HEADER_SIZE = 4 # ----> 3?
TRACE_LENGTH = 700
NUM_BYTES= TRACE_LENGTH * 2 + RADC_HEADER_SIZE + RADC_PKG_HEADER_SIZE


# https://docs.python.org/3/library/struct.html
# NeuDet36.pdf page 7
SAMPLE_BYTES = 2
# f_sample = 'c' # 1 Byte (has to be split)
f_sample = 'h' # 2 Bytes per sample (has to be split)
# f_samples = f'{TRACE_LENGTH*SAMPLE_BYTES}{f_sample}'
f_samples = TRACE_LENGTH * f_sample
f_pkgheader = 'cb 2s' # 1+1+2 Bytes: Type, Number, unknown rest
# f_radc_header = 'BBH 3sB II' # 16 = 1+1+2+3+1+4+4 Bytes (Event header)
f_radc_header = 'bbh 3sb ii' # 16 = 1+1+2+3+1+4+4 Bytes (Event header)

f_file = f"!{f_pkgheader} {f_radc_header} {f_samples}"


wfm_dict = {
    "channel":  None,
    "Trigger_info":  None,
    "event_ID":  None,
    "energy": None,
    "multiplicity": None,
    "subsecs": None,
    "seconds": None,
}

def print_binary(my_bytes):
    if isinstance(my_bytes, bytes):
        for my_byte in my_bytes:
            print(f'{my_byte:0>8b}', end=' ')
    elif isinstance(my_bytes, int):
        print(bin(my_bytes))
    else:
        print(f"Unknown type: {my_bytes} ({type(my_bytes)})")
    print("")

def show_binary(unpacked):
    f_ = f"{f_pkgheader} {f_radc_header}"
    repacked = struct.pack(f_, *unpacked[0:10])
    print_binary(repacked)


def unpack_waveform(filecontents, f_file=f_file):
    print(f"f_file: {f_file}")

    unpacked = struct.unpack(f_file, filecontents)
    return unpacked


def unpack_binary(filecontents, f_file=f_file):
    print(f"f_file: {f_file}")

    unpacked = struct.iter_unpack(f_file, filecontents)
    return unpacked

def extract_from_binary(unpacked):
    return list(unpacked)[0]


def read_file(testfile):

    file = os.path.join(testfolder, subfolder, testfile)
    with open(file, 'rb') as file:
        # read as bytes object
        filecontents = file.read()

    lengf = struct.calcsize(f_file)
    count = len(filecontents) / lengf
    print(f"> File {testfile}: {len(filecontents)} Bytes ({count} times {lengf})")

    if testfile.endswith("wfm"):
        unpacked = unpack_waveform(filecontents)
    else:
        unpacked = unpack_binary(filecontents)

    # print(len(unpacked), type(unpacked))
    # print(type(unpacked))
    if not isinstance(unpacked, tuple):
        unpacked = extract_from_binary(unpacked)

    print(len(unpacked))
    show_binary(unpacked)

    pkgheader = {
        "PKG_TYPE": unpacked[0],
        "PKG_NUMBER": unpacked[1],
        "PKG_REST": unpacked[2],
    }

    wfm_dict = {
        "channel":  unpacked[3],
        "Trigger_info": unpacked[4],
        "event_ID": unpacked[5],
        "energy": unpacked[6],
        "multiplicity": unpacked[7],
        "subsecs": unpacked[8],
        "seconds": unpacked[9],
    }

    first_sample = {
        "total": unpacked[10],
        "Trigger": bool((unpacked[10] >> 15) & 1),
        "Inhibit": bool((unpacked[10] >> 14) & 1),
        "value": unpacked[19] & 0b0011111111111111,
    }

    print("pkgheader:", pkgheader)
    print(wfm_dict)
    print("first_sample: (1: True)", first_sample)

    # https://realpython.com/python-bitwise-operators/#bitmasks



# read_file(testfile_wfm)
read_file(testfile_bin)



