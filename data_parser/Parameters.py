from pandas import read_csv
from pathlib import Path
from scipy.interpolate import interp1d
import numpy as np
import pickle

directory = Path(__file__).parent / 'tables'
match_pulse_maximum = False
add_old_columns = False
limit_trigger_region_us = 0.2
max_distance_accidental_coincidence = 2 #included
flag_dictionary = {'s': 10, 'b': 1, 'p': 10000, 'n': 0, 'u': 0, 'd': 100, 't': 1000}

# BGO pulse finding parameters
BGO_channel = 36
with open(directory / 'BGOAveragePulse.pickle', 'rb') as f:
    BGO_average_pulse = pickle.load(f) 
with open(directory / 'normFunctionBGO.pickle', 'rb') as f:
    BGO_norm_function = pickle.load(f) 
BGO_RE_threshold = 2.5 
BGO_average_pulse_cut = BGO_average_pulse[1:]

# standard pulses
with open(directory / 'average_pulse.pickle', 'rb') as f:
    average_pulse = pickle.load(f) 
with open(directory / 'normFunction.pickle', 'rb') as f:
    norm_function = pickle.load(f) 
interpolatedAveragePulse = interp1d(np.arange(len(average_pulse)), average_pulse, kind='cubic', bounds_error=False, fill_value=0)
RE_threshold = 2.5 
average_pulse_cut = average_pulse[1:]

# saturated pulses
saturationLevel = 8185
saturation_RE_threshold = 0.02

gain = 'matched_v3'
PostTriggerTime = 6250
TimeWindow = 12500

# temporary quenching function
quenching = read_csv(directory / 'neutronQuenching.txt', sep='\s+',header = None, names=['LY','Energy'])
quenching.loc[:,'LY'] = quenching.LY * 1000  # MeV to keV
quenching.loc[:,'Energy'] = quenching.Energy * 1000  # MeV to keV
birksFunction = interp1d(quenching.LY, quenching.Energy, fill_value="extrapolate")

df_energy_conversion = read_csv(directory / 'channel_map.csv')
df_energy_conversion = df_energy_conversion.sort_values('DAQ').reset_index(drop=True)
rescalingFactors = [df_energy_conversion.CE[10] / df_energy_conversion.CE[i] for i in range(len(df_energy_conversion))]
if gain == 'matched_v2':
    rescalingFactors = [df_energy_conversion.CE2[10] / df_energy_conversion.CE2[i] for i in range(len(df_energy_conversion))]
if gain == 'matched_v3':
    rescalingFactors = [df_energy_conversion.CE3[10] / df_energy_conversion.CE3[i] for i in range(len(df_energy_conversion))]
constant = np.array(df_energy_conversion['Constant'])
slope = np.array(df_energy_conversion['Slope'])

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

########################################################################################

# legacy pulse finding parameters
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
