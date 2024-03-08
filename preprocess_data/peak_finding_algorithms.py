from pathlib import Path
import uproot
import scipy as sp
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import data_parser
data_parser.init("v2")
from data_parser import data_io, struct_conversion
from time import process_time

#
# Todo: Split uproot and root export in separate file to keep dependencies minimal
# Todo: add uproot to requirements.txt (generate as described in README)
#


class Parameters:
    # these first 3 are only for the scipy function to find the peaks
    sp_height = 10
    sp_width = int(12)
    sp_distance = int(2)  # samples 

    height = 10  # it was 0.6 mV for now it's in ADC counts
    width = int(12)

    number_of_sample_below_thres_for_range = int(3)
    max_number_of_pulses = int(1)
    sample_width = int(16)  # ns
    n_samples_baseline = int(10)


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
    peak_max_index = peak_window_start + np.argmax(samples[peak_window_start: peak_window_end + 1])

    # here a moving average of 3 points is made
    sig_windows_start = np.flip(samples[: (peak_max_index + 2)])
    # taking the averages starting at peak_max + 1 so the average is centered around the current index
    #                       one before peak         peak                    one after
    averaged_sig_window = sig_windows_start[:-2] + sig_windows_start[1:-1] + sig_windows_start[2:]
    averaged_sig_window = np.multiply(averaged_sig_window, 1./3.)

    # finds the pulse start by finding in reverse the first index where signal is less than height
    pulse_start = peak_max_index - \
        find_first_n_less(min_threshold_height,
                          averaged_sig_window, n_below_min)
    # same for the pulse_end
    # 3 wide box car average centered on each value (-1 current_index +1)
    sig_windows_end = samples[peak_max_index - 1:]
    averaged_sig_window = sig_windows_end[:-2] + \
        sig_windows_end[1:-1] + sig_windows_end[2:]
    averaged_sig_window = np.multiply(averaged_sig_window, 1./3.)

    pulse_end = peak_max_index + find_first_n_less(min_threshold_height, averaged_sig_window, n_below_min)

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
        pulse_max_index = pulse_start + np.argmax(samples[pulse_start: pulse_end + 1])
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
    sig_boxcar = sp.ndimage.uniform_filter1d(
        samples * Parameters.sp_width, size=Parameters.sp_width
    )

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


    num_pulses = min(len(peaks), Parameters.max_number_of_pulses)
    if num_pulses == 0:
        successes.append(False)
        max_indices.append(0)
        pulse_heights.append(0)
        pulse_widths.append(0)
        areas.append(0) 
        starts.append(0)
        ends.append(0)

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
                                      Parameters.n_samples_baseline:start_pulse]
            baseline = np.mean(baseline_sample)
        elif len(samples[end_pulse:]) >= Parameters.n_samples_baseline:
            baseline_sample = samples[end_pulse:
                                      Parameters.n_samples_baseline + end_pulse]
            baseline = np.mean(baseline_sample)
        else:
            baseline = 0

        # subtract them to create baselined signal
        samples = samples - baseline*np.ones(len(samples))

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

    return successes, max_indices, pulse_heights, pulse_widths, areas, starts, ends


def update_dataframe_with_pulses(df: pd.DataFrame,window_length = 200) -> pd.DataFrame:
    '''
    It adds the columns with the pulses parameters to the dataframe
    '''
    # they took the same time
    # df[['IsPulse', 'MaxIndex', 'PulseHeight','PulseWidth','Charge','StartPulse','EndPulse']] = pd.DataFrame(
    #     np.row_stack(np.vectorize(pulse_operations, otypes=['O'])(df['samples'])),
    #     index=df.index
    #     )
    if 'snippets' in df.columns:
        df = data_io.explode_dataframe(df)
    tmp = df['samples'].apply(pulse_operations)
    
    columns=['IsPulse', 'MaxIndex', 'PulseHeight', 'PulseWidth', 'Charge',
        'StartPulse', 'EndPulse']
    for i,col in enumerate(columns):
        df[col] = [row[i] for row in tmp]
    df = df.explode(['IsPulse', 'MaxIndex', 'PulseHeight', 'PulseWidth', 'Charge',
        'StartPulse', 'EndPulse']).reset_index(drop=True)

    return df


def df_to_root_file(pdf: pd.DataFrame, out_dir: str, namefile: str) -> uproot.writing.writable.WritableDirectory:
    '''
    It creates the root file using the dataframe. Some columns are converted to suitable 
    types for uproot. Attention: it creates automatically the folder
    '''
    if data_parser.VERSION == 2:
        pdf=pdf.explode(['trigger_IDs']).reset_index(drop=True)
        #pdf.loc[:, 'Info_flags'] = pdf.Info_flags.astype('str')
        pdf=pdf.drop(columns='Info_flags')
    if data_parser.VERSION == 1:
        pdf.loc[:, 'Type'] = pdf.Type.astype('str')
        pdf.loc[:, 'Rest'] = pdf.Rest.astype('str')
    
    pdf = pdf[pdf.IsPulse == True]
    pdf.loc[:, 'Datetime'] = pdf['Datetime'].dt.strftime('%Y%m%d')
    pdf.loc[:, 'Datetime'] = pdf.Datetime.astype('int64')
    pdf = pdf.drop(columns='IsPulse')
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    file = uproot.recreate(out / (namefile + ".root"))
    file['eventsTree'] = pdf
    return file


def single_dataset_to_root(data_dir: str, input_filename: str, out_dir: str, output_filename: str, **kwargs):
    '''
    Function to convert the datafile directly to a rootdir
    '''
    tracelength = kwargs.pop('tracelength',64)
    window_length = kwargs.pop('window_length',200)
    df = struct_conversion.DataFile(
        Path(data_dir) / input_filename,
        tracelength=tracelength
    )
    pdf = data_io.make_total_dataFrame([df])
    pdf = update_dataframe_with_pulses(pdf,window_length = window_length)
    file = df_to_root_file(pdf, out_dir, output_filename)
    return file




if __name__ == '__main__':
    data_parser.init('v1')
    df = struct_conversion.DataFile(
        "BC230705b_04-2_65ns_60mv_stretched_readout.bin",
        tracelength=100
        #"BG231005b_05-1_Switch-Delock_0dB_30-8_65ns_60mV_10_readout.01.bin"
    )

    pdf = data_io.make_total_dataFrame([df])
    start = process_time()
    pdf = update_dataframe_with_pulses(pdf)
    print(f'Time needed to process the dataset: {process_time() - start: .2f} s.')
    selectedPulses = pdf.Charge[(pdf.Charge < 980) & (pdf.Charge > 860)]
    print(f'Area = ({np.mean(selectedPulses):.1f} +/- {np.std(selectedPulses):.1f}) ADC counts')
    print(f'Total number of pulses: {len(pdf.Charge[pdf.IsPulse==True])}.')
    plt.hist(pdf.Charge, bins=300)
    plt.xlabel('ADC counts')
    plt.ylabel('counts')
    plt.xlim([860, 980])
    plt.savefig('areas.pdf')
    df_to_root_file(pdf, '.', 'test')
