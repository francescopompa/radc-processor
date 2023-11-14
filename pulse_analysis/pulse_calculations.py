"""
Module providing calculation functions for found pulses.
"""
import numpy as np
import pandas as pd
import itertools


def get_baseline_avg(row):
    """
    Cuts the samples making the peak and calculates the average over
    the remaining ones.
    WARNING: only works for a single pulse per Snippet!
    """
    List = (
        row["samples"][:row["Limits"][0]]
        + row["samples"][row["Limits"][1]+1:-1] # Exclude last sample, as it's always 0
        )
    return np.mean(List)

def get_limits(x):
    """
    Apply to column.
    Returns a tuple of the left and right pulse limits per row.
    (Assumes only one peak per row of samples)
    """
    return x[1]["left_bases"][0], x[1]["right_bases"][0]

def add_samples(row):
    """Shift pulse by BaselineCorr and return sum of all pulse samples."""
    return sum(
        [i - row["BaselineCorr"]
        for i in row["samples"][row["Limits"][0]:row["Limits"][1]+1]]
        )

def fix_overflows(row, column="samples", threshold=-2000):
    """
    Fix sign overflows in ADC counts (represented as 14 bit signed int).

    14 bit unsigned integers have a range from 0 to 2**14 - 1.
    14 bit signed integers have a range from -2**13 to 2**13 - 1.

    This function returns the samples list corrected in a way that:

    if one negative sample is more than half the value range away from
    the previous sample, and that sample is positive;
    then the negative sample and all following samples up to the last
    sample before a comparable inverse jump,
    are corrected by an offset equal to the length of the value range.

    This means that sign overflows where the real value of the overflow-
    sample is higher than half the value range plus the value of the
    previous sample, are not detected.
    """
    samples = row[column] if column else row
    upper_range = pd.Interval(left=2**12 -1, right=2**13 -1, closed="both") # [4095,8191]
    lower_range = pd.Interval(left=-2**13, right=-2**12, closed="both")     # [-8192, -4096]
    offset = (2**13) + (2**13 -1)

    # early exit if no correction necessary
    if all(s not in lower_range for s in samples):
        return samples

    # Get regions where samples are in the upper range
    high = [i for i,s in enumerate(samples) if s in upper_range]
    between = [
        (high[_j-1]+1, i-1)
        for _j,i in enumerate(high)
        if _j>0 and i!=high[_j-1]+1
        ]

    # look at interruptions between those regions
    need_correction =[]
    for left_end, right_end in between:
        if (samples[left_end] in lower_range
        and samples[right_end] in lower_range):
            need_correction += range(left_end, right_end+1)

    # correct samples within those interruptions
    for index in need_correction:
        samples[index] = samples[index] + offset

    return samples
    # return [i if i > threshold else 8192+8192+i for i in a] # i is negative in else case



def adjust_baseline(data):
    """
    Calculates columns "Limits", "BaselineCorr" and "Sum" inplace for data.
    Assumes one pulse per row.
    """
    data["Limits"] = data["PeakFinding"].apply(get_limits)
    data["BaselineCorr"] = data.apply(get_baseline_avg, axis=1)
    data["Sum"] = data[["samples", "Limits", "BaselineCorr"]].apply(add_samples, axis=1)


def get_peak_to_peak(row, column="samples"):
    """
    Returns peak-to-peak distance of the samples within the samples list.
    Uses a simple abs(max()-min()) calculation and no statistics/averaging.
    """
    samples = row[column] if column else row
    return abs(max(samples)-min(samples))


def detect_saturation(row, column="samples"):
    """
    Returns the list of sample indices from the samples list;
    where each entry marks one sample index of a chain where
        - the sample value is >= the maximum of the value range
        AND
        - the sample value is equal to the previous sample value or the
            following sample value.

    If no saturation is detected, the returned list is empty ([]).
    Using pandas, test the presence/absence of saturation using

        .astype(bool)   # False if is an empty list

    The value range is determined as 2**13-1 (for 14bit signed integers)
    """
    samples = row[column] if column else row
    max = 2**13-1

    return [
        i+1
        for i,s in enumerate(samples[1:-1])
        # if i>0
        if s>=max
        and (s==samples[i-1+1] or s==samples[i+1+1])
        ]
    # [i for j,i in enumerate(high) if j>0 and i == high[j-1]+1]


def detect_flatlines(row, column="samples", bandwidth=5):
    """
    Returns True if the value range of a waveform is limited to
    bandwidth, hinting at a (mostly) flat waveform not showing any information.

    Returns False if max(samples) - min(samples) > bandwidth

    Rightmost samples with value 0 are stripped from the waveform beforehand.
    """
    samples = row[column] if column else row

    # strip zero values at (right) end of the samples
    stripped_samples = list(itertools.dropwhile(lambda x: x == 0, samples[::-1]))

    # Compare value range to bandwidth
    return (max(stripped_samples)-min(stripped_samples)) <= bandwidth

    #
    # Todo:
    # Expand by giving a threshold of n waveforms to keep, and increase
    # bandwidth parameter until onle n waveforms remain.
    #


def detect_sharp_peaks(row, column="samples", threshold=4096, count=5):
    """
    Returns True if the samples list contains single samples that are
    at least `threshold` above from their neighbours.
    """
    samples = row[column] if column else row
    exceeding = [
        i+1
        for i,s in enumerate(samples[1:-1])
        if s - samples[i-1+1] > threshold
        and s - samples[i+1+1]> threshold
    ]
    return len(exceeding) > 0
    # nb_samples = len(samples)
    # average = sum(samples)/nb_samples
    # above = [s for s in samples if s > average]
    # return len(above) < count

    # for i in exceeding:
    #     samples[i] = (samples[i+1]+samples[i-1])/2

    # return samples