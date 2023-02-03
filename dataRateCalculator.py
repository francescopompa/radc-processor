
"""Calculates data rates and volumes necessary for various scenarios
"""
import bitmath
import math

variables = {
    "driveSpeeds": {
        # per Second
        "HDD": {
            "readMin": bitmath.MiB(180),
            "readMax": bitmath.MiB(250),
            "writeSmallF": bitmath.MiB(1),
            "writeMin": bitmath.MiB(80),
            "writeMax": bitmath.MiB(160),
            "size": bitmath.TiB(8),
        },
        "SSD": {
            "readMin": bitmath.MiB(2500),
            "readMax": bitmath.MiB(3500),
            "writeMin": bitmath.MiB(1500),
            "writeMin": bitmath.MiB(3000),
            "size": bitmath.TiB(2),
        },
        "USB3.2": {
            "min": bitmath.Gib(5),
            "max": bitmath.Gib(10),
        },
        "USB4": {
            "min": bitmath.Gib(10),
            "max": bitmath.Gib(40),
        },
    },
    "channels": {
        "all": 36
    },
    "samples": {
        "time": 0.016, # us (16ns)
    },
    "packages": {
        "size": {
            "max": bitmath.Byte(1420),
        },
        "headerSize": {
            "max": bitmath.Byte(20),
        },
        "samplesMax": {
            # each two Bytes long
            "max": 700,
        },
    },
    "bandwidth": {
        # "bits_s": 1e9, # 1Gb/s
        # "bytes_s": 1e9 / 8,
        "max": bitmath.Gib(1),
    },
    "neutronRate": {
        # Rate of _registered_ neutron events
        "estimate": 0.001,
        "highEstimate": 10, # Hz
        "lowCalibration": 100,
        "highCalibration": 200,
    },
    "gammaRate": {
        "highCalibration": 1000,
    },
    "lookTime": {
        # us
        "gammaShort": 1,
        "gammaLong": 5,
        "backwards": 100,
        "backAndForw": 200,
    },
    "duration": {
        # in Seconds
        "oneHour": 3600,
        "oneDay": 86400,
        "oneWeek": 86400*7,
        "threeMonths": 7948800,
    },

}

scenarios = {
    "neutronMeasurement": {
        "worstCase": {
            # "eventRate": variables["neutronRate"]["highCalibration"],
            "eventRate": variables["neutronRate"]["highEstimate"],
            "snippetCount": 50,
            "snippetSize": bitmath.Byte(100), # Bytes
        },
        "estimatedAverage": {

        },
    },
    "neutronCalibration": {
        "worstCase": {
            "eventRate": variables["neutronRate"]["highCalibration"],
            "timeWindow": variables["lookTime"]["backAndForw"],
        },
        "estimatedAverage": {

        }

    },
    "gammaCalibration": {
        "worstCase": {
            "eventRate": variables["gammaRate"]["highCalibration"],
            "timeWindow": variables["lookTime"]["gammaLong"],
        },
        "estimatedAverage": {

        },
    }
}


def meas_raw_data_rate(
    eventRate, # Hz
    snippetCount,# Snippets
    snippetSize, # Bytes
):
    return eventRate * (snippetCount * snippetSize)

def cali_raw_data_rate(
    eventRate, # Hz
    timeWindow, # us
    channels = variables["channels"]["all"],
    sampleTime = variables["samples"]["time"], # us
    packageHeader = variables["packages"]["headerSize"]["max"], # Bytes
    packageSamplesMax = variables["packages"]["samplesMax"]["max"],
):
    samples = math.ceil(timeWindow / sampleTime)

    return eventRate * channels * (
        bitmath.Byte(2)*samples
        + packageHeader*math.ceil(samples/packageSamplesMax)
    )

def raw_data_volume(
    duration, # s
    dataRate, # Bytes/s
    rateUnit = "Bytes",
):
    if rateUnit == "Bytes":
        Bytes = duration * dataRate
        bits = duration * dataRate * 8
    else:
        Bytes = duration * dataRate / 8
        bits = duration * dataRate

    return duration * dataRate


def format_rate(rate, pct = ""):
    rate_B = rate.best_prefix()
    rate_b = rate_B.to_Gib().format('{value:.5f} {unit}')

    return f"Data rate: {rate_B.format('{value:.2f} {unit}')}/s ({pct*100:.2f}% of the bandwidth: {rate_b}/s) ({rate})"

def format_volume(volume):
    v = volume.best_prefix()
    return f"Total volume: {v.format('{value:.3f} {unit}')} ({volume})"

def compare_drive(drive, rate, volume):
    Capacity = int(drive["size"] / volume)
    Read = "yes" if rate <= drive["readMin"] else "no"
    Write = "yes" if drive["writeMin"] <= rate <= drive["writeMax"] else "no"

    if "writeSmallF" in drive:
        # HDD
        WriteSmallFiles = "yes" if rate <= drive["writeSmallF"] else "no"
    else:
        # SSD
        WriteSmallFiles = "yes"

    Transfer = "?"

    return Capacity, Read, Write, WriteSmallFiles, Transfer

def compare_cable(cable, rate):
    Read = "min" if rate <= cable["min"] else "max" if rate <= cable["max"] else "no"
    Write = "min" if rate <= cable["min"] else "max" if rate <= cable["max"] else "no"
    Transfer = "?"

    return " ", Read, Write, " ", Transfer


def format_comparison_table(rate, volume):

    header = ["Capacity", "Read", "Write", "WriteSmallFiles", "Transfer (read+write)"]
    index = ["Type", f"HDD {variables['driveSpeeds']['HDD']['size']}", f"SSD {variables['driveSpeeds']['SSD']['size']}", "USB3.2", "USB4"]

    HDD = compare_drive(variables["driveSpeeds"]["HDD"], rate, volume)
    SSD = compare_drive(variables["driveSpeeds"]["SSD"], rate, volume)
    USB3 = compare_cable(variables["driveSpeeds"]["USB3.2"], rate)
    USB4 = compare_cable(variables["driveSpeeds"]["USB4"], rate)

    for i, row in enumerate([header, HDD, SSD, USB3, USB4]):
        print('| {:{i1}} | {:{h0}} | {:{h1}} | {:{h2}} | {:{h3}} | {:{h4}} |'.format(
            index[i], *row,
            i1 = max([len(x) for x in index]),
            h0 = len(header[0]),
            h1 = len(header[1]),
            h2 = len(header[2]),
            h3 = len(header[3]),
            h4 = len(header[4]),
            ))
        #print(index[i], *row)


def process_scenario(durationName, scenarioName, variantName="worstCase"):
    duration = variables["duration"][durationName]
    scenario = scenarios[scenarioName][variantName]

    if scenarioName.endswith("Calibration"):
        rate = cali_raw_data_rate(**scenario)
    elif scenarioName.endswith("Measurement"):
        rate = meas_raw_data_rate(**scenario)

    volume = raw_data_volume(duration, rate)
    ratePct = rate / variables["bandwidth"]["max"].to_Byte()

    if ratePct > 1:
        volume = volume / ratePct

    print(f"\nScenario: {durationName} {scenarioName} - {variantName}")
    # print(rate, volume, ratePct)
    print(format_rate(rate, ratePct))
    print(format_volume(volume))

    format_comparison_table(rate, volume)


def main():
    process_scenario("threeMonths", "neutronMeasurement")
    process_scenario("oneHour", "neutronCalibration")
    process_scenario("oneHour", "gammaCalibration")




if __name__ == "__main__":
    main()
