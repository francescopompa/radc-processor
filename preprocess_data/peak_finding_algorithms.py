import data_parser
data_parser.init("v2")

from . import Parameters
from time import process_time
from data_parser import data_io, struct_conversion
from pathlib import Path
import uproot
import scipy as sp
import pandas as pd
import matplotlib.pyplot as plt
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
    averaged_sig_window = sig_windows_start[:-2] + \
        sig_windows_start[1:-1] + sig_windows_start[2:]
    averaged_sig_window = np.multiply(averaged_sig_window, 1./3.)

    # finds the pulse start by finding in reverse the first index where signal is less than height
    pulse_start = peak_max_index - \
        find_first_n_less(min_threshold_height,
                          averaged_sig_window, n_below_min) - 2
    # same for the pulse_end
    # 3 wide box car average centered on each value (-1 current_index +1)
    sig_windows_end = samples[peak_max_index - 1:]
    averaged_sig_window = sig_windows_end[:-2] + \
        sig_windows_end[1:-1] + sig_windows_end[2:]
    averaged_sig_window = np.multiply(averaged_sig_window, 1./3.)

    pulse_end = peak_max_index + \
        find_first_n_less(min_threshold_height,
                          averaged_sig_window, n_below_min) + 2

    if pulse_start >= len(samples):
        pulse_start = len(samples) - 1
    if pulse_end >= len(samples):
        pulse_end = len(samples) - 1

    # check if pulse index width is larger than 0
    if pulse_end - pulse_start > 0 and pulse_end != -1 and pulse_start != -1:
        pulse_width = (pulse_end-pulse_start) * Parameters.sample_width

        # Area via trapezoid integration from pulse start to end
        # ,dx=sample_width) #16 ns sample width
        pulse_area = np.trapz(samples[pulse_start: pulse_end + 1])
        try:
            pulse_max_index = pulse_start + \
                np.argmax(samples[pulse_start: pulse_end + 1])
        except ValueError:
            return False, 0, 0, 0, 0, 0, 0
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
    samples = np.array(samples)
    if samples.any() == np.nan:
        samples = np.zeros(64)
    try:
        sig_boxcar = sp.ndimage.uniform_filter1d(
            samples * Parameters.sp_width, size=Parameters.sp_width
        )
    except np.AxisError:
        return False, 0, 0, 0, 0, 0, 0

    peaks, peak_properties = sp.signal.find_peaks(
        sig_boxcar,
        height=Parameters.sp_height * Parameters.sp_width,
        distance=Parameters.sp_distance,
    )
    successes = []
    max_indices = []
    pulse_heights = []
    pulse_widths = []
    areas = []
    starts = []
    ends = []
    baselines = []

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

        if len(samples[:start_pulse]) >= Parameters.n_samples_baseline:
            baseline_sample = samples[start_pulse -
                                      Parameters.n_samples_baseline:start_pulse+1]
            baseline = np.mean(baseline_sample)
        elif len(samples[end_pulse:]) >= Parameters.n_samples_baseline:
            baseline_sample = samples[end_pulse:
                                      Parameters.n_samples_baseline + end_pulse + 1]
            baseline = np.mean(baseline_sample)
        else:
            baseline = np.mean(samples[-5:])

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


def update_dataframe_with_pulses(df: pd.DataFrame) -> pd.DataFrame:
    '''
    It adds the columns with the pulses parameters to the dataframe
    '''

    if 'snippets' in df.columns:
        df = data_io.explode_dataframe(df)
    tmp = df['samples'].apply(pulse_operations)

    columns = ['IsPulse', 'MaxIndex', 'PulseHeight', 'PulseWidth', 'Charge',
               'StartPulse', 'EndPulse', 'Baseline']
    for i, col in enumerate(columns):
        df[col] = [row[i] for row in tmp]
    df = df.explode(['IsPulse', 'MaxIndex', 'PulseHeight', 'PulseWidth', 'Charge',
                     'StartPulse', 'EndPulse', 'Baseline']).reset_index(drop=True)
    length_original = len(df.index)

    if data_parser.VERSION == 2:
        # df['trigger_IDs']=[p[0] if len(p)==1 else 0 for p in df['trigger_IDs']]
        # pdf.loc[:, 'Info_flags'] = pdf.Info_flags.astype('str')
        df = df.drop(columns='Info_flags')
    if data_parser.VERSION == 1:
        df.loc[:, 'Type'] = df.Type.astype('str')
        df.loc[:, 'Rest'] = df.Rest.astype('str')

    # checking data corruption
    # this part will be removed later to find the pulse detection efficiency
    df = df[df.IsPulse == True]
    df = df.drop(columns='IsPulse')
    df = df[(df.Channel_number < 36) & (df.Channel_number >= 0)]

    df['Charge_keV'] = df.apply(lambda x: energyConversion(
        x['Charge'], x['Channel_number'], Parameters.gain), axis=1)
    df['samples_mV'] = df.apply(lambda x: ADC_to_mV_conversion(
        x['samples'], x['Channel_number']), axis=1)
    df['deltaT_us'] = df.apply(lambda x: getRelativeTimeSnippets(
        x['Subsecs'], x['Timedelta_samples'], Parameters.PostTriggerTime), axis=1)

    df.loc[:, 'Datetime'] = df['Datetime'].dt.strftime('%Y%m%d')
    df.loc[:, 'Datetime'] = df.Datetime.astype('int64')
    # set explicit types to columns if possible
    df['BoxcarSum'] = df['samples'].apply(getBoxcarSum)

    # this part is necessary to reindex the snippets in case of bad data
    tmp = df.groupby('Event_ID')
    for (event_ID), event_DF in tmp:
        if len(event_DF.index) < event_DF['snippet_space'].iloc[0]:
            df.loc[df['Event_ID'] == event_ID,
                   'snippet_space'] = len(event_DF.index)
            df.loc[df['Event_ID'] == event_ID, 'Snippet_number'] = range(
                1, len(event_DF.index)+1)

    df = df.sort_values(['Event_ID', 'Snippet_number'])
    df.index = pd.RangeIndex(len(df.index))
    df.index = range(len(df.index))
    if len(df.index) < length_original:
        print(
            f'The total number of events is {len(df.index)/length_original:.1%} of the original due to corrupted data.')
    print(f'Number of events: {len(df.index)}')
    return df


def df_to_root_file(df: pd.DataFrame, out_dir: str, namefile: str) -> uproot.writing.writable.WritableDirectory:
    '''
    It creates the root file using the dataframe. Attention: it creates automatically the folder
    '''
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    file = uproot.recreate(out / (namefile + ".root"))
    file['eventsTree'] = df
    return file


def single_dataset_to_root(data_dir: str, input_filename: str, out_dir: str, output_filename: str, **kwargs):
    '''
    Function to convert the datafile directly to a rootdir
    '''
    tracelength = kwargs.pop('tracelength', 64)
    df = struct_conversion.DataFile(
        Path(data_dir) / input_filename,
        tracelength=tracelength
    )
    pdf = data_io.make_total_dataFrame([df])
    pdf = update_dataframe_with_pulses(pdf)
    file = df_to_root_file(pdf, out_dir, output_filename)
    return file


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
    E_keV = (charge + 624)/16.36 * rescalingFactor
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
        print(f'The channel {channel} does not exist!')
        return list(samples / 32.7)


def getRelativeTimeSnippets(subseconds, timedelta_samples, PostTriggerTime):
    sampling_period = 16e-3
    dT = (subseconds % 2**16) - timedelta_samples

    if dT < 0:
        return ((2**16 + dT) - PostTriggerTime) * sampling_period
    else:
        return (dT - PostTriggerTime)*sampling_period


def getBoxcarSum(samples):
    samples_averaged = np.convolve(samples, np.ones(4)/4, mode='valid')
    rolling_sum = np.convolve(samples_averaged, np.ones(
        Parameters.T_time), mode='valid')
    return max(rolling_sum)


if __name__ == '__main__':
    data_parser.init('v1')
    df = struct_conversion.DataFile(
        "BC230705b_04-2_65ns_60mv_stretched_readout.bin",
        tracelength=100
        # "BG231005b_05-1_Switch-Delock_0dB_30-8_65ns_60mV_10_readout.01.bin"
    )

    pdf = data_io.make_total_dataFrame([df])
    start = process_time()
    pdf = update_dataframe_with_pulses(pdf)
    print(
        f'Time needed to process the dataset: {process_time() - start: .2f} s.')
    selectedPulses = pdf.Charge[(pdf.Charge < 980) & (pdf.Charge > 860)]
    print(
        f'Area = ({np.mean(selectedPulses):.1f} +/- {np.std(selectedPulses):.1f}) ADC counts')
    print(f'Total number of pulses: {len(pdf.Charge[pdf.IsPulse==True])}.')
    plt.hist(pdf.Charge, bins=300)
    plt.xlabel('ADC counts')
    plt.ylabel('counts')
    plt.xlim([860, 980])
    plt.savefig('areas.pdf')
    df_to_root_file(pdf, '.', 'test')
