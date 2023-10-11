
import os
import struct
import json

testfolder = r"U:\WS22-23 (MA) Masterarbeit\RADC_testData"

subfolder = "2023-01-10_PulsTrigger" # Enthält viele mehrfache Trigger ❌
testfile_bin = "radc_nd.bin" # len(filecontents):
testfile_bin = "radc.bin.3" # len(filecontents):
testfiles = ["radc_nd.bin", "radc_nd.bin.1", "radc.bin.3"]

# subfolder = "2023-01-20_UDP" # Enthält viele mehrfache Trigger ❌
# testfile_bin = "test.bin" # len(filecontents): 11 597 140 Bytes = 8167 * 1420
# testfile_wfm = "ND00000000.wfm"
# testfiles = ["test.bin"]

subfolder = "2023-02-07_PulsTrigger" # Enthält keine mehrfachen Trigger ✔️
testfile_bin = "2023-02-07.bin" # len(filecontents):
testfiles = ["2023-02-07.bin", "2023-02-07.bin.3", "2023-02-07.bin.4", "radc_nd.bin"]

subfolder = "2023-03-01_PulseGen"
testfile_bin = "radc.1.bin" # len(filecontents):
#testfiles = ["2023-02-07.bin", "2023-02-07.bin.3", "2023-02-07.bin.4", "radc_nd.bin"]


# Format of a single UDP-Package:
RADC_HEADER_SIZE = 16
RADC_PKG_HEADER_SIZE = 4 # ----> 3?
TRACE_LENGTH = 700
NUM_BYTES= TRACE_LENGTH * 2 + RADC_HEADER_SIZE + RADC_PKG_HEADER_SIZE


# https://docs.python.org/3/library/struct.html
# NeuDet36.pdf page 7
SAMPLE_BYTES = 2
f_sample = 'h' # 2 Bytes per sample (has to be split)
f_samples = TRACE_LENGTH * f_sample
f_pkgheader = 'cB 2s' # 1+1+2 Bytes: Type, Number, unknown rest
f_radc_header = 'BBH 3sB II' # 16 = 1+1+2 + 3+1 4+4 Bytes (Event header)

# ! Requires Little-Endian! (<)
f_file = f"<{f_pkgheader} {f_radc_header} {f_samples}"

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
    # print(f"f_file: {f_file}")

    unpacked = struct.unpack(f_file, filecontents)
    return unpacked


def unpack_binary(filecontents, f_file=f_file):
    # print(f"f_file: {f_file}")

    unpacked = struct.iter_unpack(f_file, filecontents)
    return unpacked

def extract_from_binary(unpacked):
    return list(unpacked)[0]


def ununpack_package(unpacked):
    # print(len(unpacked))

    pkgheader = {
        "PKG_TYPE": unpacked[0],
        "PKG_NUMBER": unpacked[1],
        "PKG_REST": unpacked[2],
    }

    tmp = unpacked[6]

    wfm_dict = {
        "chan.":  unpacked[3],
        "trigg_inf": unpacked[4],
        "event_ID": unpacked[5],
        "energy": int.from_bytes(bytes([tmp[2], tmp[1], tmp[0]])),
        "mult.": unpacked[7],
        "subsecs": unpacked[8],
        "seconds": unpacked[9],
    }

    samples = []
    for sample in unpacked[10:]:
        t = bool((sample >> 15) & 1)
        i = bool((sample >> 14) & 1)
        unsigned_val = sample & 0b0011111111111111
        s = unsigned_val >> 13 # 1: negative, 0:positive

        # Sofern der ADC das 2er Komplement verwendet (und nicht Magnitude oder 1er Komplement)
        value = -s*2**14 + unsigned_val

        samples.append({
            "total": bin(sample),
            "RealTrigger": t and not i,
            # "Trigger": t,
            # "Inhibit": i,
            # "value": (sample  & 0b0011111111111111) - (1<<14) - 2, # für negative Werte
            # "value": (sample  & 0b0011111111111111) # für Positive Werte (< Hälfte von  2**14)
            "value": value,
        })

    return pkgheader, wfm_dict, samples



def format_unpacked(pkgheader, wfm_dict, samples):

    print("Package:", pkgheader)

    maxi = {"value": 0}
    mini = {"value": 0}
    triggers = {"count": 0, "sample_IDs": []}

    print(wfm_dict)
    # print("first_sample: (1=True)", samples[0])
    for id, sample in enumerate(samples):
        # if id == 0:
        #     print(f"  {id:03} {sample}")
        if sample["RealTrigger"]:
            triggers["count"] += 1
            triggers["sample_IDs"].append(id)
            # print(f"  {id:03} {sample}")

        # print(f"  {id:03} {sample}")
        if sample["value"] > maxi["value"]: maxi = sample
        if sample["value"] < mini["value"]: mini = sample

    # print("max:", maxi)
    # print("min:", mini)
    if triggers["count"] > 1:
        print(f"{pkgheader['PKG_NUMBER']}: (eID {wfm_dict['event_ID']}) Real Triggers: {triggers}")



    # https://realpython.com/python-bitwise-operators/#bitmasks


def read_file(testfile):

    file = os.path.join(testfolder, subfolder, testfile)
    with open(file, 'rb') as file:
        # read as bytes object
        filecontents = file.read()

    lengf = struct.calcsize(f_file)
    count = len(filecontents) / lengf
    print(f"> File {testfile}: {len(filecontents)} Bytes ({count} times {lengf})")
    if len(filecontents) == 0:
        return

    if testfile.endswith("wfm"):
        unpacked = unpack_waveform(filecontents)
    else:
        unpacked = unpack_binary(filecontents)

    # print(len(unpacked), type(unpacked))
    # print(type(unpacked))
    if not isinstance(unpacked, tuple):

        # unpacked = extract_from_binary(unpacked)
        # pkgheader, wfm_dict, samples =  ununpack_package(unpacked)
        # format_unpacked(pkgheader, wfm_dict, samples)

        for npckd in unpacked:
            show_binary(npckd)
            pkgheader, wfm_dict, samples =  ununpack_package(npckd)
            format_unpacked(pkgheader, wfm_dict, samples)

            yield [pkgheader, wfm_dict, samples]
    else:
        show_binary(unpacked)

        pkgheader, wfm_dict, samples =  ununpack_package(unpacked)
        format_unpacked(pkgheader, wfm_dict, samples)

        return [pkgheader, wfm_dict, samples]




if __name__ == "__main__":
    # read_file(testfile_wfm)
    read_file(testfile_bin)

    # for file in testfiles:
    #     read_file(file)



