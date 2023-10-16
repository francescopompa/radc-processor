from import_helper import *
list_imports()
import matplotlib.pyplot as plt
import tqdm
import scipy as sp
from numba import jit,njit
import uproot
from pathlib import Path

class Parameters:
    height=10 #it was 0.6 mV for now it's in ADC counts
    width=12
    distance=2 #ns #it's for sure more
    number_of_sample_below_thres_for_range=3
    max_number_of_pulses=1
    sample_width=16
    chunk_size=int(1e3)

#@jit(nopython=True, cache=True)
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

#@njit(nopython=True, cache=True)
def divide_in_chunks(pulses):
    """
    it separates the 2d array in chunks
     """
    n=Parameters.chunk_size
    print(n)
    for i in range(pulses.shape[0] // n + 1):
        yield pulses[n*i:n*(i+1),:]

#@njit(nopython=True, cache=True)
def calc_puls_params(pulse, peak, min_threshold_height, window_size, n_below_min):
    """
    part of pulse_finder function
    :param n_below_min:
    :param pulse:
    :param peak:
    :param min_threshold_height:
    :param window_size:
    :return:
    """
    #time=np.array([16*i for i,_ in enumerate(pulse)])
    # recalculate the peak based on the boxcar signal,
    # into one where we search in peak +- window size of the actual signal
    peak_window_start = peak - window_size
    peak_window_end = peak + window_size

    if peak_window_end >= len(pulse):
        peak_window_end = len(pulse) - 1
    if peak_window_start <= 1:
        peak_window_start = 0

    # searching for the signal peak in the given window around the smoothed peak
    peak_max_index = peak_window_start + np.argmax(pulse[peak_window_start : peak_window_end + 1])

    # here a moving average of 3 points is made
    sig_windows_start = np.flip(pulse[: (peak_max_index + 2)])
    # taking the averages starting at peak_max + 1 so the average is centered around the current index
    #                       one before peak         peak                    one after
    averaged_sig_window = sig_windows_start[:-2] + sig_windows_start[1:-1] + sig_windows_start[2:]
    averaged_sig_window = np.multiply(averaged_sig_window,1./3.) 

    # finds the pulse start by finding in reverse the first index where signal is less than height
    pulse_start = peak_max_index - find_first_n_less(min_threshold_height, averaged_sig_window, n_below_min)
    # same for the pulse_end
    # 3 wide box car average centered on each value (-1 current_index +1)
    sig_windows_end = pulse[peak_max_index - 1 :]
    averaged_sig_window = sig_windows_end[:-2] + sig_windows_end[1:-1] + sig_windows_end[2:]
    averaged_sig_window = np.multiply(averaged_sig_window,1./3.) 

    # TODO i just check and the box car average should change nothing about the index position right?
    pulse_end = peak_max_index + find_first_n_less(min_threshold_height, averaged_sig_window, n_below_min)

    if pulse_start >= len(pulse):
        pulse_start = len(pulse) - 1
    if pulse_end >= len(pulse):
        pulse_end = len(pulse) - 1
    
    # check if pulse index width is larger than 0
    if pulse_end - pulse_start > 0 and pulse_end != -1 and pulse_start != -1:
        pulse_width = (pulse_end-pulse_start)*Parameters.sample_width

        # Area via trapezoid integration from pulse start to end
        pulse_area = np.trapz(pulse[pulse_start : pulse_end + 1])#,dx=sample_width) #16 ns sample width
        pulse_max_index = pulse_start + np.argmax(pulse[pulse_start : pulse_end + 1])
        if pulse_max_index <= pulse_start or pulse_end <= pulse_max_index:
            # max height could not be found so just using peak from smoothed signal
            pulse_max_index = peak
        pulse_height = pulse[pulse_max_index]
        return True, pulse_max_index, pulse_height, pulse_width, pulse_area, pulse_start, pulse_end
    return False, 0, 0, 0, 0, 0, 0

#@njit(nopython=True, cache=True)      
def pulse_operations(samples):
        
    #chunk_size=np.shape(samples)[0]
    success = np.array([])
    max_index = np.array([])
    pulse_height=np.array([])
    pulse_width= np.array([])
    area=np.array([])
    start=np.array([])
    end=np.array([])
        
        
        
    for sample in samples:
        # TODO could be turned into unevenly weighted sum but works rn
        sig_boxcar = sp.ndimage.uniform_filter1d(
        sample * Parameters.width, size=Parameters.width
        )
        # Find Peaks using the box car summed signal (the factors have to be multiplied of course)
        # The peaks are only searched from trig index on
        peaks, peak_properties = sp.signal.find_peaks(
            sig_boxcar,
            height=Parameters.height * Parameters.width,
            distance=Parameters.distance,
            )

        # Calculate pulse
        num_pulses = min(len(peaks), Parameters.max_number_of_pulses)


        
        index_of_peak_sorted = np.argsort(peak_properties["peak_heights"])
        peaks_sorted = np.flip(peaks[index_of_peak_sorted])
        if num_pulses==0:
            success=np.append(success,False)
            max_index=np.append(max_index,0)
            pulse_height=np.append(pulse_height,0)
            pulse_width=np.append(pulse_width,0)
            area=np.append(area,0)
            start=np.append(start,0)
            end=np.append(end,0)
                     
        for _, peak in enumerate(peaks_sorted[:num_pulses]):
            
            s, max_i, pulse_h, pulse_w, area_pulse, start_pulse, end_pulse = calc_puls_params(
                sample,
                peak,
                Parameters.height,
                Parameters.width,
                Parameters.number_of_sample_below_thres_for_range
                )
                    
            baseline_sample = sample[start_pulse-60:start_pulse-10] 
            if len(baseline_sample>0):   
                baseline = np.mean(baseline_sample)
            else: baseline=0
            # subtract them to create baselined signal
            sample = sample-baseline*np.ones(len(sample))
                    
            s, max_i, pulse_h, pulse_w, area_pulse, start_pulse, end_pulse = calc_puls_params(
                sample,
                peak,
                Parameters.height,
                Parameters.width,
                Parameters.number_of_sample_below_thres_for_range
                )
            success=np.append(success,s)
            max_index=np.append(max_index,max_i)
            pulse_height=np.append(pulse_height,pulse_h)
            pulse_width=np.append(pulse_width,pulse_w)
            area=np.append(area,area_pulse)
            start=np.append(start,start_pulse)
            end=np.append(end,end_pulse)
        




    return success, max_index, pulse_height, pulse_width, area, start, end


#@jit(nopython=True, cache=True)
def loop_over_events(all_samples):

    event_number = 0
    n_events=np.shape(all_samples)[0]
    # tqdm_chunk_progressbar = tqdm.tqdm(total=len(chunked_arrays[0]) + 1, desc="chunks")
    print(f"{n_events // Parameters.chunk_size +1 } chunks with size of {Parameters.chunk_size} events")
    tqdm_event_progressbar = tqdm.tqdm(
        total=n_events // Parameters.chunk_size +1,
        desc="Chunks",
        )
    successes=np.array([])
    max_indices=np.array([])
    pulse_heights=np.array([])
    pulse_widths=np.array([])
    areas=np.array([])
    starts=np.array([])
    ends=np.array([])
        
    for _, chunk_samples in enumerate(divide_in_chunks(all_samples)):
        #sorry for the bad naming, in reality they all should be plural
        success, max_index, pulse_height, pulse_width, area, start, end = pulse_operations(chunk_samples)
        successes=np.append(successes,success)
        max_indices=np.append(max_indices,max_index)
        pulse_heights=np.append(pulse_heights,pulse_height)
        pulse_widths=np.append(pulse_widths,pulse_width)
        areas=np.append(areas,area)
        starts=np.append(starts,start)
        ends=np.append(ends,end)
        tqdm_event_progressbar.update()
        event_number += Parameters.chunk_size

    return successes,max_indices,pulse_heights,pulse_widths,areas,starts,ends

def df_to_root_file(df,out_dir,namefile):
    pdf=pdf[pdf.IsPulse==True]
    pdf=pdf.drop(columns=['samples'])
    pdf=pdf.drop(columns=['Timestamp_s','Datetime'])
    pdf=pdf.drop(columns=['Type','Rest','trigger_IDs'])
    pdf=pdf.drop(columns='IsPulse')
    pdf
    file = uproot.recreate(Path(out_dir) / (namefile + ".root") )
    file['eventsTree']=pdf
    file['eventsTree'].show()
                    

if __name__=='__main__':
    df = struct_conversion.DataFile(
    "/Users/francesco/Desktop/neutron_detector/electronics/radc-processor/bin_to_root/BC230705b_04-2_65ns_60mv_stretched_readout.bin",
    tracelength=100
    #"/Users/francesco/Desktop/neutron_detector/electronics/radc-processor/bin_to_root/BG231005b_05-1_Switch-Delock_0dB_30-8_65ns_60mV_10_readout.01.bin"
    )

    pdf = data_io.make_total_dataFrame([df])

    #pdf.drop(labels=["Type", "Rest", "min", "max", "trigger_count", "Multiplicity", "Trigger_info"], axis="columns")

    pulses=np.array(pdf.samples)
    pulses=np.stack(pulses,axis=0)


    #print(pulses)
    n_events=np.shape(pulses)[0]
    print(f'Total number of events: {n_events}')
    successes,max_indices,pulse_heights,pulse_widths,areas,starts,ends = loop_over_events(pulses) 
    print(np.mean(areas[(areas<960) & (areas>900)]))
    print(np.std(areas[(areas<960) & (areas>900)]))
    print(len(areas))
    print(len(successes))
    nTrue=0
    for s in successes:
        if s==True:
            nTrue+=1
    print(nTrue)
    plt.hist(areas,bins=300)
    plt.xlim([860,980])
    plt.show()

    pdf['IsPulse']=successes
    pdf['MaxIndex']=max_indices
    pdf['PulseHeights']=pulse_heights
    pdf['PulseWidths']=pulse_widths
    pdf['Charge']=areas
    pdf['StartPulse']=starts
    pdf['EndPulse']=ends
    print(pdf.columns)
    df_to_root_file(pdf,'.','test.root')