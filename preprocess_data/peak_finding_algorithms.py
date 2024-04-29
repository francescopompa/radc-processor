import data_parser
data_parser.init("v2")

from . import Parameters
from time import time
from pathlib import Path
import scipy as sp
import pandas as pd
import numpy as np

#
# Todo: Split uproot and root export in separate file to keep dependencies minimal
# Todo: add uproot to requirements.txt (generate as described in README)
#


def find_first_n_less(min_value, vector, n):
    """
    walks the vector until its values where n times consecutive below min value
    then returns the first index under of the n times below min value
    eg. f( 1, [1.5, 0., -1., -1.5.], 2) would return index 1
    """
    less_than_count = 0
    for indx, val in enumerate(vector):
        if val < min_value:
            less_than_count += 1
        else:
            less_than_count = 0

        if less_than_count >= n:
            return indx - round(n / 2 + 0.5)
    if less_than_count == 0:
        idx = (np.abs(vector - min_value)).argmin()
        return idx
    else:
        return 0


def calc_puls_params(samples, peak, min_threshold_height, window_size, n_below_min):
    """
    part of pulse_finder function
    :param n_below_min:
    :param pulse:
    :param peak:
    :param min_threshold_height:
    :param window_size:
    :return:
    It returns the pulse parameters once the peak is found through scipy
    For now only one pulse per snippet
    """
    # recalculate the peak based on the boxcar signal,
    # into one where we search in peak +- window size of the actual signal
    peak_window_start = peak - window_size
    peak_window_end = peak + window_size

    if peak_window_end >= len(samples):
        peak_window_end = len(samples) - 1
    if peak_window_start <= 1:
        peak_window_start = 0
    # searching for the signal peak in the given window around the smoothed peak
    peak_max_index = peak_window_start + \
        np.argmax(samples[peak_window_start: peak_window_end + 1])

    # here a moving average of 3 points is made
    sig_windows_start = np.flip(samples[: (peak_max_index + 2)])
    # taking the averages starting at peak_max + 1 so the average is centered around the current index
    #                       one before peak         peak                    one after
    averaged_sig_window = np.convolve(sig_windows_start,np.ones(Parameters.n_samples_baseline)/Parameters.n_samples_baseline,mode = 'valid')

    # finds the pulse start by finding in reverse the first index where signal is less than height
    pulse_start = peak_max_index - \
        find_first_n_less(min_threshold_height,
                          averaged_sig_window, n_below_min)
    if samples[pulse_start] > (Parameters.height +5):
        pulse_start = max(0,pulse_start -10)
    # same for the pulse_end
    # 3 wide box car average centered on each value (-1 current_index +1)
    sig_windows_end = samples[peak_max_index - 1:]
    averaged_sig_window = np.convolve(sig_windows_end, np.ones(Parameters.n_samples_running_average)/Parameters.n_samples_baseline,mode = 'valid')

    n_samples = find_first_n_less(min_threshold_height,
                          averaged_sig_window, n_below_min) 
    pulse_end = peak_max_index + n_samples
    pulse_width = pulse_end-pulse_start
    if n_samples == 0:
        pulse_end = 63
    elif pulse_width < 30:
        pulse_end = min(pulse_start + 40, 63)
        
    if pulse_start >= len(samples):
        pulse_start = len(samples) - 1
    if pulse_end >= len(samples):
        pulse_end = len(samples) - 1

    # check if pulse index width is larger than 0
    if pulse_end - pulse_start > 0 and pulse_end != -1 and pulse_start != -1:
        
        pulse_width = pulse_end - pulse_start
        # Area via trapezoid integration from pulse start to end
        # ,dx=sample_width) #16 ns sample width
        pulse_area = np.trapz(samples[pulse_start: pulse_end + 1])
        try:
            pulse_max_index = pulse_start + \
                np.argmax(samples[pulse_start: pulse_end + 1])
        except ValueError:
            pulse_max_index = peak
        if pulse_max_index <= pulse_start or pulse_end <= pulse_max_index:
            # max height could not be found so just using peak from smoothed signal
            pulse_max_index = peak
        pulse_height = samples[pulse_max_index]
        return True, pulse_max_index, pulse_height, pulse_width, pulse_area, pulse_start, pulse_end
    return False, 0, 0, 0, 0, 0, 0


def pulse_operations(samples: list | pd.Series):
    """
    The procedure implemented here is the following:
    1. The pulses are found with scipy find_peaks
    2. They are ordered by height
    3. Only the number decided by the Parameters class will be processed
    4. For each peak, the pulse parameters are computed once for the first time to determine the start of the pulse
    5. The baseline is computed with samples before the pulse
    6. The parameters of the pulse are computed again and returned
    Support for multiple pulses per snippet
    """
    successes = []
    max_indices = []
    pulse_heights = []
    pulse_widths = []
    areas = []
    starts = []
    ends = []
    baselines = []

    samples = np.array(samples)
    if samples.any() == np.nan:
        samples = np.zeros(64)
    try:
        sig_boxcar = sp.ndimage.uniform_filter1d(
            samples * Parameters.sp_width, size=Parameters.sp_width
        )
    except np.AxisError:
        return [False], [0], [0], [0], [0], [0], [0], [0]


    peaks, peak_properties = sp.signal.find_peaks(
        sig_boxcar,
        height=Parameters.sp_height * Parameters.sp_width,
        distance=Parameters.sp_distance,
    )
    
    num_pulses = min(len(peaks), Parameters.max_number_of_pulses)
    if num_pulses == 0:
        successes.append(False)
        max_indices.append(0)
        pulse_heights.append(0)
        pulse_widths.append(0)
        areas.append(0)
        starts.append(0)
        ends.append(0)
        baselines.append(0)

    index_of_peak_sorted = np.argsort(peak_properties["peak_heights"])
    peaks_sorted = np.flip(peaks[index_of_peak_sorted])

    for _, peak in enumerate(peaks_sorted[:num_pulses]):

        _, _, _, _, _, start_pulse, end_pulse = calc_puls_params(
            samples,
            peak,
            Parameters.height,
            Parameters.width,
            Parameters.number_of_sample_below_thres_for_range
        )

        
        baseline = np.mean(samples[:Parameters.n_samples_baseline+1])

        # subtract them to create baselined signal
        samples = samples - baseline
        success, max_index, pulse_height, pulse_width, area, start, end = calc_puls_params(
            samples,
            peak,
            Parameters.height,
            Parameters.width,
            Parameters.number_of_sample_below_thres_for_range
        )
        successes.append(success)
        max_indices.append(max_index)
        pulse_heights.append(pulse_height)
        pulse_widths.append(pulse_width)
        areas.append(area)
        starts.append(start)
        ends.append(end)
        baselines.append(baseline)

    return successes, max_indices, pulse_heights, pulse_widths, areas, starts, ends, baselines

def naive_pulse_operations(samples):
    samples = np.array(samples)
    baselines = [np.mean(samples[:5])]
    samples = samples-baselines[0]
    max_indices = [np.argmax(samples)]
    successes = [True]
    pulse_heights = [samples[max_indices[0]]]
    starts = [11]
    ends = [63]
    pulse_widths = [63 - 11]
    areas = [np.trapz(samples[11:])]
    return successes, max_indices, pulse_heights, pulse_widths, areas, starts, ends
    


def energyConversion(charge, channel, gain='matched'):
    '''
    Function to convert ADCC to energy. 
    This function gives reliable results only in the case of full detector,
    otherwise for now it's necessary to convert in postprocessing or to use always the same channel
    with the same module
    '''
    df = pd.read_csv(Path(__file__).parent / 'channel_map_energy.csv')
    try:
        pmt = df.PMT[df['DAQ'] == channel]
        rescalingFactor = float(
            (df.CE[df.PMT == 292].item() / df.CE[pmt.index].item()))
    except ValueError:
        return -1
    E_keV = (charge + 169.3)/16.20 * rescalingFactor
    if gain == 'matched':
        return E_keV
    else:
        return E_keV / gain * 2e6


def ADC_to_mV_conversion(samples, channel):
    samples = np.array(samples)
    if channel in range(8):
        return list((samples - 13)/31.06)
    elif channel in range(8, 16):
        return list((samples - 19)/30.68)
    elif channel in range(16, 24):
        return list((samples - 19)/31.07)
    elif channel in range(24, 32):
        return list((samples - 14.06)/30.07)
    elif channel in range(32, 36):
        return list((samples - 18)/30.66)
    else:
        # print(f'The channel {channel} does not exist!')
        return list(np.zeros(64))


def getRelativeTimeSnippets(subseconds, timedelta_samples, TimeWindow, PostTriggerTime):
    sampling_period = 16e-3
    dT = (subseconds % 2**16) - timedelta_samples

    if dT < 0:
        return ((2**16 + dT) - PostTriggerTime) * sampling_period
    elif subseconds < TimeWindow:
        return (62.5e6 + dT - PostTriggerTime) * sampling_period
    else:
        return (dT - PostTriggerTime)*sampling_period

def getBoxcarSum(samples):
    samples_averaged = np.convolve(samples, np.ones(4)/4, mode='valid')
    return max(samples_averaged)*4

def getFlagsCorruptedData(channel, is_pulse, samples, timestamp):
    preprocessingFlags=''
    
    if (channel < 0) or (channel > 35) or (channel != channel):
        preprocessingFlags += 'C'
    if is_pulse == False:
        preprocessingFlags += 'P'
    if isinstance(samples,np.float64) or (isinstance(samples,list) and (len(samples) != 64)):
        preprocessingFlags += 'S'
    if timestamp > time() or timestamp < 1699000000:
        preprocessingFlags += 'T'
    return preprocessingFlags

