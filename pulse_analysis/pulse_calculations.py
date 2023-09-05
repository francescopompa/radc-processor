"""
Module providing calculation functions for found pulses.
"""
import numpy as np


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
    Returns samples but corrected in a way that:
    if samples_i < threshold, then return 2**13+2**13+samples_i
    else return samples_i
    """
    a = row[column] if column else row
    return [i if i > threshold else 8192+8192+i for i in a]


def adjust_baseline(data):
    """
    Calculates columns "Limits", "BaselineCorr" and "Sum" inplace for data.
    Assumes one pulse per row.
    """
    data["Limits"] = data["PeakFinding"].apply(get_limits)
    data["BaselineCorr"] = data.apply(get_baseline_avg, axis=1)
    data["Sum"] = data[["samples", "Limits", "BaselineCorr"]].apply(add_samples, axis=1)