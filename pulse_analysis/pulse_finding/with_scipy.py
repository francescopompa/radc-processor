"""
Module providing methods for pulse analysis and peak finding using
scipy.signal.
"""

import scipy.signal as scp


def find_peaks(row, column="PulseWaveform", **kwargs):
    """
    Wrapper for scipy.signal.find_peaks.
    Apply with

        df["PeakFinding"] = df.apply(find_peaks, axis=1)

    Return structure:
    - ?
    Options:
    - column: Name of the column of row to get the waveform from.
    If None, use row as-is instead.
    - height: Absolute minimal value of the peak sample value.
    - width: Interpolated peak width in PulseWaveform at given rel_height
    - wlen: Window length of area to inspect, centered around peak, to determine prominence and width. Cuts signal at those limits.
    - rel_height: Relative height at which peak width is measured (% of its prominence). 1.0: width of the peak at lowest contour line. 0.5: evaluates at half the prominence height.
    - plateau_size: Minimum required width in PulseWaveform of peak's flat top.
    """
    waveform = row[column] if column else row

    return scp.find_peaks(
        waveform,
        **kwargs,
    )


def get_peak_count(x):
    """Returns length of the list x of found peaks."""
    return len(x[0])


def check_finds_sanity(data, column="PeakFinding"):
    """
    Print info on found peaks and checks problematic cases:
    - value_counts of the number of found peaks,
    - Number of entries without find, number of entries with more than one find.

    Returns:
    - peak_count: Series with number of found peaks
    - missed: df of entries without found peak
    - problematic: df of entries with more than one peak
    """
    peak_count = data[column].apply(get_peak_count)
    value_counts = peak_count.value_counts()
    missed = data[peak_count == 0]
    problematic = data[peak_count > 1]

    # print(peak_count)
    print(value_counts)
    print("Missed:", missed.shape, "Problematic:", problematic.shape)

    return peak_count, missed, problematic