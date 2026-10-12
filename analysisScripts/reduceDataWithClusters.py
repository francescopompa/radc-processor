import pandas as pd
import numpy as np
from glob import glob
from data_parser.data_io import build_rootfile, findAccidentalCoincidencesTriggerRegion, getClusterTimes
import gc
from pathlib import Path
from time import time
from udp_receiver.receiver_class import convert_seconds
import json
from argparse import ArgumentParser
from data_parser import Parameters


mode = 'AmB'
storageDir = '/nfs/almond/'
folder = 'FNG/AmB_140cm/'
triggerThresholds = [4000]
neutronThresholds = [0, 30, 40, 50, 60, 90, 120, 150]

parser = ArgumentParser()
parser.add_argument("-d", "--directory",
                        help=f"Sets the directory relative to {Parameters.storage_directory} where the data is stored. Default: {folder}", default=folder)
parser.add_argument("-m", "--mode",
                        help=f"Sets the mode of the data. Default: {mode}", default=mode)
parser.print_help()
args = vars(parser.parse_args())
if args['folder'] is not None:
    folder = args['folder']
    folders = [folder]
    print(f'Processing folder: {folder}...')
if args['mode'] is not None:
    mode = args['mode']
    print(f'Processing with mode: {mode}...')
if args['mode'] is not None and args['mode'] is not None:
    print('Impossible to use mode and directory at the same time.')
    exit()
print(f'Using folders {folders}')
print(f'Using trigger thresholds {triggerThresholds}')
print(f'Using neutron thresholds {neutronThresholds}')

mode = 'AmB'
if mode == 'AmB':
    folders = ['AmB_140cm','AmB_170cm','AmB_190cm','AmB_200cm','AmB_310cm']
    folders = [f'FNG/{f}' for f in folders]
    triggerThresholds = [4000]
    neutronThresholds = [0, 30, 40, 50, 60, 90, 120, 150]
    clusterEnergyFunction = np.max 
elif mode == 'DD':
    folders = ['DD_3MeV','DD_3MeV_withShadowCone']
    folders = [f'FNG/{f}' for f in folders]
    triggerThresholds = [2500]
    neutronThresholds = [0]
    clusterEnergyFunction = np.sum



columns_to_save = ['Event_ID','Timestamp_s','ApproxEnergy_keVee','PulseTime_us','triggerEnergy']
AmB_folders = ['AmB_90cm','AmB_140cm','AmB_170cm','AmB_190cm','AmB_200cm','AmB_310cm']



def birksLawSum(energies,birksFunction):
    quenchedEnergies = birksFunction
    (energies)
    return np.sum(quenchedEnergies)


start = time()



def scaleEnergies(energy,channel,calib,folder):
    folder = folder.split('/')[-1]
    try:
        return energy * calib['AmB_140cm'][10] / calib[folder][channel]
    except:
        return energy

calib = {}
for folder in AmB_folders:
    calibrationDir = f'{storageDir}/{folder}/gammaCalibration/gammaCalibrationResults'
    cal = pd.read_csv(f'{calibrationDir}/gammaCalibrationResults_{folder}.csv')
    cal = cal.sort_values(by='channel')
    calib[folder] = cal.Min_derivative.values
    calib[folder][26] = 3420 # therefore it must be reprocessed in theory
    print(calib[folder][10])


for folder in folders:
    dir=f'{storageDir}/{folder}/processed/'
    
    print(f'Processing folder: {folder}...')

    fraction_accidental_coincidences_list = []
    events_without_accidental_coincidences_list = []

    outputGammaDir = f'{storageDir}/{folder}/gammaCalibration/'
    efficiencyDirectory = f'{storageDir}/{folder}/efficiency/'
    p = Path(outputGammaDir)
    p.mkdir(parents=True, exist_ok=True)
    p = Path(efficiencyDirectory)
    p.mkdir(parents=True, exist_ok=True)

    files = glob(f'{dir}/*.pickle')
    files.sort()


    parts = []
    times_dfs = []
    j=0
    for i,f in enumerate(files):

        tmp = pd.read_pickle(f)
        tmp = tmp[tmp.Channel_number.isin(range(36))]
        if mode == 'AmB':
            tmp.loc[:,'ApproxEnergy_keVee'] = tmp.apply(lambda row: scaleEnergies(row.ApproxEnergy_keVee,row.Channel_number,calib,folder),axis=1)

        tmp_trigger = tmp[tmp.PulseTime_us.between(-0.1,0.1)].reset_index(drop=True)
        tmp_trigger = tmp_trigger[tmp_trigger.AveragePulsePass]

        
        findAccidentalCoincidencesTriggerRegion(tmp_trigger)
        
        fraction_accidental_coincidences = tmp_trigger[tmp_trigger.AccidentalCoincidenceFlag].Event_ID.nunique()/tmp_trigger.Event_ID.nunique()
        fraction_accidental_coincidences_list.append(fraction_accidental_coincidences)
        # print(f'Fraction of accidental coincidences in the trigger region: {fraction_accidental_coincidences:.3%}')
        tmp_trigger = tmp_trigger[tmp_trigger.AccidentalCoincidenceFlag == False].reset_index(drop=True)
        tmp = tmp[tmp.AveragePulsePass].reset_index(drop=True)
        
        
        triggerEnergy = tmp_trigger.groupby('Event_ID').agg({'ApproxEnergy_keVee':'sum'})
        tmp.loc[:,'triggerEnergy'] = tmp.Event_ID.map(triggerEnergy.ApproxEnergy_keVee)
        tmp = tmp[np.abs(tmp.PulseTime_us) > 0.2] 
        
        parts.append(tmp[columns_to_save])
        del tmp
        gc.collect()
        E_th = 0
        
        if (i % 10 == 0 and i > 0) or i == len(files)-1:
            df = pd.concat(parts, ignore_index=True)
            for E_th in triggerThresholds:
                df_th = df[df.triggerEnergy > E_th].reset_index(drop=True)
                clusters = df_th.groupby('Event_ID').apply(getClusterTimes,neutronThresholds=neutronThresholds,clusterEnergyFunction=clusterEnergyFunction,include_groups=False)
                clusters_data = clusters.apply(lambda x: pd.Series({
                'clusters': x[0],
                'clusterEnergies': x[1],
                'sumEnergyDictionaries': x[2],
                'clusterMultiplicity': x[3]
                }))
                df_th = df[df.triggerEnergy > E_th].drop(columns=['ApproxEnergy_keVee','PulseTime_us']).drop_duplicates('Event_ID').reset_index(drop=True)
                df_th = df_th.join(clusters_data, on='Event_ID')
                df_th = df_th.explode(['clusters', 'clusterEnergies','sumEnergyDictionaries','clusterMultiplicity']).reset_index(drop=True)
                df_th = pd.concat([df_th.drop('sumEnergyDictionaries', axis=1), pd.DataFrame(df_th['sumEnergyDictionaries'].tolist(), index=df_th.index)], axis=1)
                df_th = df_th.dropna(subset=['triggerEnergy']).reset_index(drop=True)
                
                p = Path(efficiencyDirectory)
                p.mkdir(parents=True, exist_ok=True)
                df_th.to_pickle(f'{efficiencyDirectory}/times_{j}_{E_th}keV.pickle')
                build_rootfile(df_th,{},efficiencyDirectory,f'times_{j}_{E_th}keV',0)
                print(f'Saved time calibration part {j} and capture threshold {E_th} keV with {df_th.Event_ID.nunique():,} events.')
            print(f'Loaded {files.index(f)+1}/{len(files)} files...')
            del df
            j+=1
            parts = []
            print(f'Elapsed time: {convert_seconds(time() - start)}.')
    with open(f'{efficiencyDirectory}/fraction_accidental_coincidences.json', 'w') as fp:
        json.dump({'fraction_accidental_coincidences':np.mean(fraction_accidental_coincidences_list)}, fp,indent=4)



print(f'Elapsed time: {convert_seconds(time() - start)}.')