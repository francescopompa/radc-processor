from import_helper import *
#list_imports()
import matplotlib.pyplot as plt
import scipy as sp
import uproot
from pathlib import Path
import time


class Parameters:
    sp_height=int(10) #these first 3 are only for the scipy function to find the peaks
    sp_width=int(12)
    sp_distance=int(2) #samples #it's for sure more
    
    height=int(10) #it was 0.6 mV for now it's in ADC counts
    width=int(12)
    
    number_of_sample_below_thres_for_range=int(3)
    max_number_of_pulses=int(1)
    sample_width=int(16) #ns
    n_samples_baseline=int(50)

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
    peak_max_index = peak_window_start + np.argmax(samples[peak_window_start : peak_window_end + 1])

    # here a moving average of 3 points is made
    sig_windows_start = np.flip(samples[: (peak_max_index + 2)])
    # taking the averages starting at peak_max + 1 so the average is centered around the current index
    #                       one before peak         peak                    one after
    averaged_sig_window = sig_windows_start[:-2] + sig_windows_start[1:-1] + sig_windows_start[2:]
    averaged_sig_window = np.multiply(averaged_sig_window,1./3.) 

    # finds the pulse start by finding in reverse the first index where signal is less than height
    pulse_start = peak_max_index - find_first_n_less(min_threshold_height, averaged_sig_window, n_below_min)
    # same for the pulse_end
    # 3 wide box car average centered on each value (-1 current_index +1)
    sig_windows_end = samples[peak_max_index - 1 :]
    averaged_sig_window = sig_windows_end[:-2] + sig_windows_end[1:-1] + sig_windows_end[2:]
    averaged_sig_window = np.multiply(averaged_sig_window,1./3.) 

    pulse_end = peak_max_index + find_first_n_less(min_threshold_height, averaged_sig_window, n_below_min)

    if pulse_start >= len(samples):
        pulse_start = len(samples) - 1
    if pulse_end >= len(samples):
        pulse_end = len(samples) - 1
    
    # check if pulse index width is larger than 0
    if pulse_end - pulse_start > 0 and pulse_end != -1 and pulse_start != -1:
        pulse_width = (pulse_end-pulse_start)*Parameters.sample_width

        # Area via trapezoid integration from pulse start to end
        pulse_area = np.trapz(samples[pulse_start : pulse_end + 1])#,dx=sample_width) #16 ns sample width
        pulse_max_index = pulse_start + np.argmax(samples[pulse_start : pulse_end + 1])
        if pulse_max_index <= pulse_start or pulse_end <= pulse_max_index:
            # max height could not be found so just using peak from smoothed signal
            pulse_max_index = peak
        pulse_height = samples[pulse_max_index]
        return True, pulse_max_index, pulse_height, pulse_width, pulse_area, pulse_start, pulse_end
    return False, 0, 0, 0, 0, 0, 0

def pulse_operations(samples: list|pd.Series):
        
    samples=np.array(samples)
    sig_boxcar = sp.ndimage.uniform_filter1d(
    samples * Parameters.sp_width, size=Parameters.sp_width
    )
    
    peaks, peak_properties = sp.signal.find_peaks(
        sig_boxcar,
        height=Parameters.sp_height * Parameters.sp_width,
        distance=Parameters.sp_distance,
        )

    num_pulses = min(len(peaks), Parameters.max_number_of_pulses)
    if num_pulses==0:
        success=False
        max_index=0
        pulse_height=0
        pulse_width=0
        area=0
        start=0
        end=0


        
    index_of_peak_sorted = np.argsort(peak_properties["peak_heights"])
    peaks_sorted = np.flip(peaks[index_of_peak_sorted])
                     
    for _, peak in enumerate(peaks_sorted[:num_pulses]):
            
        _, _, _, _, _, start_pulse, _ = calc_puls_params(
            samples,
            peak,
            Parameters.height,
            Parameters.width,
            Parameters.number_of_sample_below_thres_for_range
            )
                    
        baseline_sample = samples[start_pulse-10-Parameters.n_samples_baseline:start_pulse-10] 
        if len(baseline_sample)>0:   
            baseline = np.mean(baseline_sample)
        else: baseline=0
        # subtract them to create baselined signal
        samples = samples-baseline*np.ones(len(samples))
                    
        success, max_index, pulse_height, pulse_width, area, start, end = calc_puls_params(
            samples,
            peak,
            Parameters.height,
            Parameters.width,
            Parameters.number_of_sample_below_thres_for_range
            )
            
    return success, max_index, pulse_height, pulse_width, area, start, end


def update_dataframe_with_pulses(df: pd.DataFrame):
    #they took the same time
    df[['IsPulse', 'MaxIndex', 'PulseHeight','PulseWidth','Charge','StartPulse','EndPulse']] = pd.DataFrame(
        np.row_stack(np.vectorize(pulse_operations, otypes=['O'])(df['samples'])), 
        index=df.index
        ) 
    #df[['IsPulse', 'MaxIndex', 'PulseHeight','PulseWidth','Charge','StartPulse','EndPulse']]=df['samples'].apply(pulse_operations).to_list()  
    return df

def df_to_root_file(pdf,out_dir,namefile):
    print(f'Ratio of pulses detected: {len(pdf[pdf.IsPulse==True])/len(pdf.IsPulse):.1%}')
    pdf=pdf[pdf.IsPulse==True]
    pdf.loc[:,'Datetime'] = pdf['Datetime'].dt.strftime('%Y%m%d')
    pdf.loc[:,'Datetime']=pdf.Datetime.astype('int64')
    pdf.loc[:,'Type']=pdf.Type.astype('str')
    pdf.loc[:,'Rest']=pdf.Rest.astype('str')
    pdf=pdf.drop(columns='IsPulse')
    pdf
    file = uproot.recreate(Path(out_dir) / (namefile + ".root") )
    file['eventsTree']=pdf
    file['eventsTree'].show()

def data_to_root(data_dir: str,input_filename: str,tracelength: int,out_dir: str,output_filename: str):
    start=time.process_time()
    df = struct_conversion.DataFile(
    Path(data_dir) / input_filename,
    tracelength=tracelength
    )
    pdf = data_io.make_total_dataFrame([df])
    pdf = update_dataframe_with_pulses(pdf)
    df_to_root_file(pdf,out_dir,output_filename)
    print(f'Total time needed to process the dataset: {time.process_time() - start:.1f} s.')



                    

if __name__=='__main__':
    start1=time.process_time()
    df = struct_conversion.DataFile(
    #"/Users/francesco/Desktop/neutron_detector/electronics/radc-processor/preprocess_data/BC230705b_04-2_65ns_60mv_stretched_readout.bin",
    #tracelength=100
    "/Users/francesco/Desktop/neutron_detector/electronics/radc-processor/preprocess_data/BG231005b_05-1_Switch-Delock_0dB_30-8_65ns_60mV_10_readout.01.bin"
    )

    pdf = data_io.make_total_dataFrame([df])
    start = time.process_time()
    pdf = update_dataframe_with_pulses(pdf)
    print(f'Time needed to process the dataset (only pulse finding): {time.process_time() - start:.1f} s.')
    print(f'Area = ({np.mean(pdf.Charge[(pdf.Charge <980) & (pdf.Charge>860)]):.1f} +/- {np.std(pdf.Charge[(pdf.Charge <980) & (pdf.Charge>860)]):.1f}) ADC counts')
    print(len(pdf.Charge))
    plt.hist(pdf.Charge,bins=300)
    plt.xlabel('ADC counts')
    plt.ylabel('counts')
    plt.xlim([860,980])
    plt.savefig('areas.pdf')

    df_to_root_file(pdf,'.','test')
    print(f'Total time needed to process the dataset: {time.process_time() - start1:.1f} s.')
