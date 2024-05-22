from pandas import read_csv
from pathlib import Path

# these first 3 are only for the scipy function to find the peaks
sp_height = 10
sp_width = int(12)
sp_distance = int(20)  # samples

height = 10
width = int(12)

number_of_sample_below_thres_for_range = int(5)
max_number_of_pulses = int(1)
sample_width = int(16)  # ns
n_samples_baseline = int(3)
n_samples_running_average = 5


gain = 'matched'
T_time = 10
PostTriggerTime = 6250
TimeWindow = 12500

df_energy_conversion = read_csv(Path(__file__).parent / 'channel_map_energy.csv')