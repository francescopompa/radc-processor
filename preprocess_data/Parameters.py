from pandas import read_csv
from pathlib import Path
import numpy as np

# these first 3 are only for the scipy function to find the peaks
sp_height = 10
sp_width = int(4)
sp_distance = int(10)  # samples


height = 10
width = int(12)

number_of_sample_below_thres_for_range = int(5)
max_number_of_pulses = int(1)
sample_width = int(16)  # ns
n_samples_baseline = int(5)
n_samples_running_average = 5

min_ratio_charge_height = 7
max_ratio_charge_height = 15


gain = 'matched'
PostTriggerTime = 6250
TimeWindow = 12500

df_energy_conversion = read_csv(Path(__file__).parent / 'channel_map_energy.csv')
df_energy_conversion = df_energy_conversion.sort_values('DAQ').reset_index(drop=True)
rescalingFactors = [df_energy_conversion.CE[10] / df_energy_conversion.CE[i] for i in range(len(df_energy_conversion))]

tiles_channels = [[32, 35, 31, 34, 30, 33],
                  [29, 26, 28, 25, 27, 24],
                  [20, 23, 19, 22, 18, 21],
                  [17, 14, 16, 13, 15, 12],
                  [11, 8, 10, 7, 9, 6],
                  [5, 2, 4, 1, 3, 0]]


coordinates = [(i[1],5-i[0]) for i,_ in np.ndenumerate(tiles_channels)]
tiles_channels = np.reshape(tiles_channels,36)

map_channels = {tiles_channels[i]:coordinates[i] for i,_ in enumerate(tiles_channels)}
inv_map_channels = {v: k for k, v in map_channels.items()}
