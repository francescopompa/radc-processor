# these first 3 are only for the scipy function to find the peaks
sp_height = 10
sp_width = int(12)
sp_distance = int(2)  # samples

height = 20  # it was 0.6 mV for now it's in ADC counts
width = int(12)

number_of_sample_below_thres_for_range = int(3)
max_number_of_pulses = int(1)
sample_width = int(16)  # ns
n_samples_baseline = int(5)
gain = 'matched'
T_time = 10
PostTriggerTime = 12500
