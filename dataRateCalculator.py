
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
            "writeSmallF": bitmath.MiB(500),
            "writeMin": bitmath.MiB(80),
            "writeMax": bitmath.MiB(160),
            "4size": bitmath.TB(4).to_TiB(),
            "8size": bitmath.TB(8).to_TiB(),
        },
        "SSD": {
            "readMin": bitmath.MiB(2500),
            "readMax": bitmath.MiB(3500),
            "writeMin": bitmath.MiB(1500),
            "writeMin": bitmath.MiB(3000),
            "1size": bitmath.TB(1).to_TiB(),
            "2size": bitmath.TB(2).to_TiB(),
        },
        "USB32G1x1": {
            "callName": "USB3.1 Gen1 (USB3.0)",
            "min": bitmath.Gib(1),
            "max": bitmath.Gib(5),
            "dual": False,
        },
        "USB32G2x1": {
            "callName": "USB3.1 Gen2 (USB3.1)",
            "min": bitmath.Gib(10),
            "max": bitmath.Gib(10),
            "dual": False,
        },
        "USB32G1x2": {
            "callName": "USB3.2 Gen1x2",
            "min": bitmath.Gib(10),
            "max": bitmath.Gib(10),
            "dual": True,
        },
        "USB32G2x2": {
            "callName": "USB3.2 Gen2x2",
            "min": bitmath.Gib(20),
            "max": bitmath.Gib(20),
            "dual": True,
        },
        "USB4": {
            "min": bitmath.Gib(10),
            "max": bitmath.Gib(40),
            "dual": False,
        },
        "Thunderbolt1": {
            "callName": "Thunderbolt 1",
            "min": bitmath.Gib(10),
            "max": bitmath.Gib(20),
            "dual": False,
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
        # Efficiency at MTU=1500B is 96%
        "max": bitmath.Gib(1) * 0.96,
        "extreme": bitmath.Gib(10) * 0.96,
    },
    "neutronRate": {
        # Rate of _registered_ neutron events
        "estimate": 2.4e-4, # 0.001,
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
    "fullBandwidth1Gbps": {
        "max": {
            "eventRate": 1,
            "snippetCount": 1,
            "snippetSize": variables["bandwidth"]["max"]
        },
    },
    "fullBandwidth10Gbps": {
        "max": {
            "eventRate": 1,
            "snippetCount": 1,
            "snippetSize": variables["bandwidth"]["extreme"]
        },
    },
    "neutronMeasurement": {
        "extreme": {
            "eventRate": variables["neutronRate"]["highCalibration"],
            "snippetCount": 50,
            "snippetSize": bitmath.Byte(100), # Bytes
        },
        "maxEstimate": {
            # "eventRate": variables["neutronRate"]["highCalibration"],
            "eventRate": variables["neutronRate"]["highEstimate"],
            "snippetCount": 50,
            "snippetSize": bitmath.Byte(100), # Bytes
        },
        "estimatedAverage": {
            "eventRate": variables["neutronRate"]["estimate"],
            "snippetCount": 50,
            "snippetSize": bitmath.Byte(100), # Bytes
        },
    },
    "Full-neutronCalibration": {
        "worstCase": {
            "eventRate": variables["neutronRate"]["highCalibration"],
            "timeWindow": variables["lookTime"]["backAndForw"],
        },
        "estimatedAverage": {
            "eventRate": variables["neutronRate"]["lowCalibration"],
            "timeWindow": variables["lookTime"]["backAndForw"],
        },
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




def meas_raw_event_size(
    eventRate,
    snippetCount,# Snippets
    snippetSize, # Bytes
):
    eventSize = snippetCount * snippetSize
    return eventSize, eventRate*eventSize

def cali_raw_event_size(
    eventRate,
    timeWindow, # us
    channels = variables["channels"]["all"],
    sampleTime = variables["samples"]["time"], # us
    packageHeader = variables["packages"]["headerSize"]["max"], # Bytes
    packageSamplesMax = variables["packages"]["samplesMax"]["max"],
):
    samples = math.ceil(timeWindow / sampleTime)
    # print("n_Samples:", samples, "per sampleTime")

    eventSize = channels * (
        bitmath.Byte(2)*samples
        + packageHeader*math.ceil(samples/packageSamplesMax)
    )
    return eventSize, eventRate*eventSize


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


def format_rate(rate, pct = "", eventRate = None, buildup=""):
    rate_B = rate.best_prefix()
    rate_b = rate_B.to_Gib().format('{value:.3g} {unit}')

    rate_2B = (2*rate).best_prefix()
    rate_2b = rate_2B.to_Gib().format('{value:.3g} {unit}')

    maxEventRate = eventRate / pct
    halfEventRate = f"--> {maxEventRate/2:.0f}Hz"
    maxEventRate = f"--> {maxEventRate:.0f}Hz"

    if pct > 1:
        newEventRate = eventRate / pct
        warning = f"""
! Bandwidth exceeded. Limiting to {variables['bandwidth']['max']}/s
  Requires limit of {int(pct)} in {math.ceil(pct)} events."""
    else:
        warning = ""
    # return f"Data rate: {rate_B.format('{value:.4g} {unit}')}/s ({pct*100:.3g}% of the bandwidth: {rate_b}/s) ({rate}/s)"
    return f"""Data rate: {rate_B.format('{value:.4g} {unit}')}/s ({pct*100:.3g}% of the bandwidth: {rate_b}/s){maxEventRate}
Data transfer: {rate_2B.format('{value:.4g} {unit}')}/s ({rate_2b}/s){halfEventRate }{buildup}{warning}"""


def format_buildup(dataRate, bandwidth, duration):
    free_bandwidth = bandwidth - dataRate
    volume = raw_data_volume(duration, dataRate)

    buildup = volume - raw_data_volume(duration, min(dataRate, free_bandwidth))
    buildup_time = buildup / bandwidth
    timePct = 100*buildup_time/duration

    if buildup_time > 3600:
        buildup_time = f"{buildup_time/3600:.0f}h"
    elif buildup_time > 60:
        buildup_time = f"{buildup_time/60:.0f}m"
    else:
        buildup_time = f"{buildup_time}s"
    buildup = buildup.best_prefix().format('{value:.3g} {unit}')


    return f"""
Data buildup 📦: {buildup} (requires an additional {buildup_time}, ~{timePct:.3g}%)"""


def format_many_events(eventSize, dataRate, eventRate, many=10000):
    format = '{value:.2f} {unit}'

    events_second = dataRate / eventSize
    hours_many = many / events_second / variables["duration"]["oneHour"]
    many_days = eventRate / many * variables["duration"]["oneDay"]
    many_Bytes = many*eventSize

    if hours_many < 0.5:
        hours_many = f"{hours_many * 60:.3g} minutes"
    else:
        hours_many = f"{hours_many:.3g} hours"

    return f"{hours_many} for {many_Bytes.best_prefix().format(format)} ({many_days:.3f} event chunks per day)."


def format_chunks(eventSize, dataRate, eventRate):
    format = '{value:.2f} {unit}'

    oneGB = bitmath.GiB(1)
    hours_oneGB = oneGB / dataRate / variables["duration"]["oneHour"]
    oneGB_days = dataRate * variables["duration"]["oneDay"]

    oneGB_events = int(oneGB / eventSize)


    if hours_oneGB < 0.5:
        hours_oneGB = f"{hours_oneGB * 60:.3g} minutes"
    else:
        hours_oneGB = f"{hours_oneGB:.3g} hours"

    return f"""Chunksizes:
  Single Event: {eventSize.best_prefix().format(format)}
  1 Gigabyte time: {hours_oneGB} for {oneGB_events} events ({oneGB_days.best_prefix().format(format)} chunks per day).
  10000 Events time: {format_many_events(eventSize, dataRate, eventRate)}
  1M Events time: {format_many_events(eventSize, dataRate, eventRate, many=1000000)}
  10M Events time: {format_many_events(eventSize, dataRate, eventRate, many=10000000)}
  20M Events time: {format_many_events(eventSize, dataRate, eventRate, many=20000000)}"""


def format_volume(volume):
    v = volume.best_prefix()
    # return f"Total volume: {v.format('{value:.3g} {unit}')} ({volume})"
    return f"Total volume: {v.format('{value:.3g} {unit}')}"

def compare_drive(drive, rate, volume, size="size"):
    Capacity = int(drive[size] / volume)
    Read = "min" if rate <= drive["readMin"] else "max" if rate <= drive["readMax"] else "no"
    Write = "min" if rate <= drive["writeMin"] else "max" if rate <= drive["writeMax"] else "no"

    if "writeSmallF" in drive:
        # HDD
        WriteSmallFiles = "yes" if rate >= drive["writeSmallF"] else "no"
        Transfer = "?"
    else:
        # SSD
        WriteSmallFiles = "yes"
        Transfer = "Only PCIe"


    return Capacity, Read, Write, WriteSmallFiles, Transfer

def compare_cable(cable, rate):
    Read = "min" if rate <= cable["min"] else "max" if rate <= cable["max"] else "no"
    Write = "min" if rate <= cable["min"] else "max" if rate <= cable["max"] else "no"
    # if cable["dual"]:
    #     Transfer = "min" if rate <= cable["min"] else "max" if rate <= cable["max"] else "no"
    # else:
    #     Transfer = "min" if rate <= cable["min"]/2 else "max" if rate <= cable["max"]/2 else "no"
    Transfer = "min" if rate <= cable["min"]/2 else "max" if rate <= cable["max"]/2 else "no"

    return " ", Read, Write, " ", Transfer


def format_comparison_table(rate, volume):
    vars = variables["driveSpeeds"]

    header = ["Capacity", "Read", "Write", "WriteSmallFiles", "Transfer (read+write)"]
    HDD4Size = variables['driveSpeeds']['HDD']['4size'].format("{value:.1f} {unit}")
    HDD8Size = variables['driveSpeeds']['HDD']['8size'].format("{value:.1f} {unit}")
    SSD1Size = variables['driveSpeeds']['SSD']['1size'].format("{value:.1f} {unit}")
    SSD2Size = variables['driveSpeeds']['SSD']['2size'].format("{value:.1f} {unit}")
    index = ["Type", f"HDD {HDD4Size}", f"HDD {HDD8Size}", f"SSD {SSD1Size}", f"SSD {SSD2Size}",
        vars["USB32G1x1"]["callName"],
        vars["USB32G2x1"]["callName"],
        vars["USB32G1x2"]["callName"],
        vars["USB32G2x2"]["callName"],
        "USB4",
        vars["Thunderbolt1"]["callName"],
        ]

    HDD4 = compare_drive(vars["HDD"], rate, volume, size="4size")
    HDD8 = compare_drive(vars["HDD"], rate, volume, size="8size")
    SSD1 = compare_drive(vars["SSD"], rate, volume, size="1size")
    SSD2 = compare_drive(vars["SSD"], rate, volume, size="2size")
    USB32G1x1 = compare_cable(vars["USB32G1x1"], rate)
    USB32G2x1 = compare_cable(vars["USB32G2x1"], rate)
    USB32G1x2 = compare_cable(vars["USB32G1x2"], rate)
    USB32G2x2 = compare_cable(vars["USB32G2x2"], rate)
    USB32G1x1 = compare_cable(vars["USB32G1x1"], rate)
    USB4 = compare_cable(vars["USB4"], rate)
    Thunderbolt1 = compare_cable(vars["Thunderbolt1"], rate)

    for i, row in enumerate([header, HDD4, HDD8, SSD1, SSD2, USB32G1x1, USB32G2x1, USB32G1x2, USB32G2x2, USB4, Thunderbolt1]):
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
    eventRate = scenario['eventRate']
    buildup = ""

    if scenarioName.endswith("Calibration"):
        eventSize, dataRate = cali_raw_event_size(**scenario)
        icon = "🎇"
    elif scenarioName.endswith("Measurement"):
        eventSize, dataRate = meas_raw_event_size(**scenario)
        icon = "🔎"
    else:
        eventSize, dataRate = meas_raw_event_size(**scenario)
        icon = "🔌"

    bandwidth = variables["bandwidth"]["max"].to_Byte()
    ratePct = dataRate / bandwidth

    if ratePct > 1:
        # volume = volume / ratePct
        dataRate = bandwidth
    if scenarioName.endswith("10Gbps"):
        icon += "✨"
        bandwidth = variables["bandwidth"]["extreme"].to_Byte()
        ratePct = dataRate / bandwidth
        dataRate = dataRate if ratePct < 1 else bandwidth

    if ratePct > 0.5:
        buildup = format_buildup(dataRate, bandwidth, duration)

    volume = raw_data_volume(duration, dataRate)


    print(f"\nScenario: {icon} {durationName} {scenarioName} - {variantName} ({eventRate} Hz)")
    # print(rate, volume, ratePct)
    print(format_rate(dataRate, ratePct, eventRate, buildup))
    print(format_chunks(eventSize, dataRate, eventRate))
    print(format_volume(volume))

    format_comparison_table(dataRate, volume)


def main():
    # print("Bandwidth limitations")
    process_scenario("threeMonths", "fullBandwidth1Gbps", variantName="max")
    process_scenario("oneHour", "fullBandwidth1Gbps", variantName="max")
    # process_scenario("threeMonths", "fullBandwidth10Gbps", variantName="max")
    # process_scenario("oneHour", "fullBandwidth10Gbps", variantName="max")

    # print("Scenarios limitations")
    process_scenario("threeMonths", "neutronMeasurement", variantName="maxEstimate")
    process_scenario("threeMonths", "neutronMeasurement", variantName="estimatedAverage")
    # process_scenario("oneHour", "neutronCalibration")
    # process_scenario("oneDay", "Full-neutronCalibration", variantName="estimatedAverage")
    process_scenario("oneHour", "Full-neutronCalibration", variantName="estimatedAverage")

    process_scenario("oneDay", "neutronMeasurement", variantName="extreme")
    process_scenario("oneHour", "neutronMeasurement", variantName="extreme")

    process_scenario("oneHour", "gammaCalibration")




if __name__ == "__main__":
    main()
