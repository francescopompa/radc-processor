import pandas as pd
import numpy as np
from glob import glob
from data_parser import Parameters
from data_parser.data_io import compactDataframe, build_rootfile, reorderEventIDs, findAccidentalCoincidencesTriggerRegion
from time import time
from udp_receiver.receiver_class import convert_seconds
import json
from pathlib import Path 
import gc
import traceback
from analysisScripts import periodicGammaCalibration
from argparse import ArgumentParser

# TO DO: rewrite it to use less RAM


storageDir = '/nfs/almond/ALMOND/'




def getTimeFromJsonFiles(files):
    """
    Extracts the time from JSON files.
    """
    total_time=0
    for file in files:
        with open(file, 'r') as f:
            data = json.load(f)
            total_time += data['total_time']
    return total_time

def correctEnergy(df,folder):
    try:
        E_cor = pd.read_csv(f'{storageDir}/{folder}/gammaCalibration/gammaCalibrationResults/gammaCalibrationResults_{folder}.csv')
        baseCF = 1.
        df['date'] = df['datetime'].dt.to_period('W-SAT').dt.start_time
        E_cor = E_cor.rename(columns={'channel':'Channel_number'})
        E_cor['date'] = pd.to_datetime(E_cor['date'])
        df = df.merge(E_cor, on=['date','Channel_number'])
        # df.loc[df['_merge'] != 'both', 'CF'] = 1.
        # df.loc[df['_merge'] != 'both', 'Fitted_CF'] = 1.
        df.loc[:,'ScaledEnergy_keVee'] = df['ApproxEnergy_keVee'] * baseCF / df['CF']
        df.loc[:,'ScaledEnergy_keVee_2'] = df['ApproxEnergy_keVee'] * baseCF / df['Fitted_CF']
        print(df[['Channel_number','ScaledEnergy_keVee_2','ScaledEnergy_keVee','ApproxEnergy_keVee','date']][df.Channel_number == 10].head())
    except Exception as e:
        print(f'Error details')
        print(f"Type: {type(e).__name__}")  
        print(f"Message: {e}")              
        print(traceback.format_exc())
        print('File not found: running first without energy correction')
        pass
    return df

def getBoxcarSum(waveform):
    boxcar_sum = np.convolve(waveform, np.ones(8), mode='valid')
    return np.max(boxcar_sum)
 

start = time()

folder = 'neutronBackground_HallB'
withEnergyCorrection = True

parser = ArgumentParser()
parser.add_argument("-d", "--directory",
                        help=f"Sets the directory relative to {Parameters.storage_directory}/ALMOND/ where the data is stored. Default: {folder}", default=folder)
parser.print_help()
args = vars(parser.parse_args())


folder = args['directory']


sumChannelThreshold = 3000
baseDir = f'{storageDir}/'
outputDir = f'{baseDir}/{folder}/reducedProcessedFiles/'
outputGammaDir = f'{baseDir}/{folder}/gammaCalibration/'
columns_to_save_reduced_file = ['Event_ID','Timestamp_s','PulseTime_us','ApproxEnergy_keVee','PulseAreaADCC','AveragePulsePass','Channel_number']
columns_to_save = ['Event_ID','Timestamp_s','PulseTime_us','PulseAreaADCC','AveragePulsePass','Channel_number', 'ApproxEnergy_keVee']
columns_for_gammaCalibration = ['Event_ID','PulseAreaADCC','ApproxEnergy_keVee','PulseTime_us','Channel_number']

signal_region = [1,100]
thr_energy=0


print(f'Reading files from {baseDir}/{folder}...')


files = glob(f'{baseDir}/{folder}/processed/*.pickle')
if folder == 'testDataset': 
    files = glob(f'{baseDir}/{folder}/*.pickle')
files.sort()

parts = []
for f in files:
    tmp = pd.read_pickle(f)
    metadata=tmp.attrs
    tmp.loc[:,'BoxcarSum'] = tmp.PulseWaveform.apply(getBoxcarSum)
    parts.append(tmp[columns_to_save_reduced_file])
    del tmp
    gc.collect()

df = pd.concat(parts, ignore_index=True)
df.attrs=metadata

df.loc[:,'Event_ID'] = reorderEventIDs(df.Event_ID)

print(f'Terminated reading {len(files)} files after {convert_seconds(time()-start)}.')
total_time = getTimeFromJsonFiles(glob(f'{baseDir}/{folder}/processed/*.json'))




df.loc[:,'datetime'] = pd.to_datetime(df.Timestamp_s, unit='s')

# Calculate the time to be subtracted
time_to_subtract_s=0
if folder=='neutronBackground_GATOR':
    dates = ['2025-05-27','2025-06-13']
    t1 = df[df['datetime']>dates[0]]['datetime'].values[0]
    t2 = df[df['datetime']<dates[1]]['datetime'].values[-1]
    time_to_subtract_s = (t2 - t1)/ np.timedelta64(1, 's')
elif folder == 'neutronBackground_HallC':
    dates = ['2025-08-23']
    t1 = df[df['datetime']<dates[0]]['datetime'].values[0]
    t2 = df[df['datetime']<dates[0]]['datetime'].values[-1]
    time_to_subtract_s = (t2 - t1)/ np.timedelta64(1, 's')
elif folder == 'neutronBackground_HallB':
    time_to_subtract_s = 0
    
print(f'Calculated time from the json: {total_time/86400:.3f} days')
print(f'Time to be subtracted: {time_to_subtract_s/86400:.3f} days')
print(f'Total time (real): {(total_time-time_to_subtract_s)/86400:.3f} days.')

days = pd.DataFrame({'TotalTime':total_time,'TimeToSubtract':time_to_subtract_s,'EffectiveTime':total_time-time_to_subtract_s,'EffectiveTime_days':(total_time-time_to_subtract_s)/86400.},index=[0])
days.to_csv(f'{outputDir}/timeInformation_{folder}.csv',index=False,float_format='%.3f')

date_groups = df.groupby(pd.Grouper(key='datetime', freq='W',label='left'))


for d in date_groups.groups:
    try:
        week = date_groups.get_group(d)
    except KeyError:
        continue
    date_str = d.strftime('%Y-%m-%d')
    print(f'Processing week starting at {date_str}...')


    for ch in range(36):
        df_ch = week[week.Channel_number==ch]
        if len(df_ch)>0:
            p = Path(f'{outputGammaDir}/{date_str}')
            p.mkdir(parents=True, exist_ok=True)
            df_ch = df_ch[columns_for_gammaCalibration].reset_index(drop=True)
            df_ch.to_pickle(f'{outputGammaDir}/{date_str}/channel{ch}.pickle')
            build_rootfile(df_ch,{},f'{outputGammaDir}/{date_str}',f'channel_{ch}',0)

periodicGammaCalibration(folder=folder)

if withEnergyCorrection: 
    df = correctEnergy(df, folder)


# not sure if really needed
findAccidentalCoincidencesTriggerRegion(df)
df = df[df.AccidentalCoincidenceFlag == False].reset_index(drop=True)
if 'ScaledEnergy_keVee' in df.columns:
    sumenergy = df[np.abs(df.PulseTime_us) < 0.1].groupby('Event_ID')['ScaledEnergy_keVee'].agg('sum')
else:
    sumenergy = df[np.abs(df.PulseTime_us) < 0.1].groupby('Event_ID')['ApproxEnergy_keVee'].agg('sum')

events3MeV = np.array(sumenergy[sumenergy > sumChannelThreshold].index)

eventsWithCoincidences=df[np.abs(df.PulseTime_us) > 0.2].Event_ID.unique()

p = Path(outputDir)
p.mkdir(parents=True, exist_ok=True)

# Take only events with coincidences and events with energy above threshold
print(f'Event above 3 MeV over total: {len(set(events3MeV))/df.Event_ID.nunique():.2%}')
print(f'Events with coincidences over total: {len(set(eventsWithCoincidences))/df.Event_ID.nunique():.2%}')
print(f'Events with coincidences above 3 MeV: {len(set(df.Event_ID[df.Event_ID.isin(np.intersect1d(events3MeV,eventsWithCoincidences))]))/df.Event_ID.nunique():.2%}')


# creation of reduced dataframes happens here
if 'ScaledEnergy_keVee' in df.columns:
    columns_to_save.append('ScaledEnergy_keVee')
    columns_to_save_reduced_file.append('ScaledEnergy_keVee')
if 'ScaledEnergy_keVee_2' in df.columns:
    columns_to_save.append('ScaledEnergy_keVee_2')
    columns_to_save_reduced_file.append('ScaledEnergy_keVee_2')

df_r=df[df.Event_ID.isin(eventsWithCoincidences)][columns_to_save].reset_index(drop=True)
df_r2= df[df.Event_ID.isin(np.intersect1d(events3MeV,eventsWithCoincidences))][columns_to_save].reset_index(drop=True)


print(f'Events in the first reduced dataframe: {df_r.Event_ID.nunique()}')
print(f'Events in the second reduced dataframe (3 MeV threshold): {df_r2.Event_ID.nunique()}')


df_r.to_pickle(f'{outputDir}/reducedProcessed.pickle')
df_r2.to_pickle(f'{outputDir}/reducedProcessed3MeVThreshold.pickle')

# root
df_r = compactDataframe(df_r)
build_rootfile(df_r,{},outputDir,'processedData',0)
df_r2 = compactDataframe(df_r2)
build_rootfile(df_r2,{},outputDir,'processedData3MeVThreshold',0)

print(f'Completed creation of reduced root files after {convert_seconds(time()-start)}.')






print(f'Time elapsed: {convert_seconds(time() - start)}.')




