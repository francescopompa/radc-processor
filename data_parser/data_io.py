from os import error
import data_parser
data_parser.init('v2')
import numpy as np
import pandas as pd
# from . import struct_conversion
from data_parser.struct_conversion import DataFile
from preprocess_data import Parameters
from preprocess_data import peak_finding_algorithms as pf
import json
import uproot
from pathlib import Path
from typing import Literal
from joblib import Parallel, delayed
import time



def datafile_to_df(file: DataFile) -> pd.DataFrame:
    """
    Read data from all Snippets in DataFile instance and return a pandas
    DataFrame.
    pandas-specific data-manipulations happen here.
    """

    df = pd.DataFrame.from_records(
        file.get_records(),
        index=None,
        exclude=None,
        columns=None,
    )

    if "Timestamp_s" in df:
        # df["Datetime"] = pd.to_datetime(df["Timestamp_s"]),
        df["Datetime"] = df["Timestamp_s"].apply(pd.Timestamp)

    return df


def load_files_to_df(files: list):
    for file in files:
        if isinstance(file, DataFile):
            yield datafile_to_df(file)
        else:
            yield datafile_to_df(DataFile(file))


def make_total_dataFrame(files: list|str) -> pd.DataFrame:

    if not isinstance(files, list):
        files = [files]

    return pd.concat(
        load_files_to_df(files),
        ignore_index=True
        )

def reorderEventIDs(series):
    # Initialize the output list with the same size
    consecutive_list = pd.Series(index=range(len(series)))
    counter = series[0]
    consecutive_list[0]=counter
    for i in range(1,len(series)):
        if series[i] != series[i-1]:  
            counter += 1
        consecutive_list[i] = counter
    
    return consecutive_list.astype(int) + 1


def preprocessDataframe(df: pd.DataFrame, TimeWindow = Parameters.TimeWindow, PostTriggerTime = Parameters.PostTriggerTime) -> pd.DataFrame:
    '''
    It adds the columns with the pulses parameters to the dataframe and calculates other useful quantities, such as the energy in keV and the time of each pulse relative to the main trigger
    '''
    print(f'Preprocessing dataframe with:\n'
          f'\t- Time window: {TimeWindow} samples\n'
          f'\t- Post trigger time: {PostTriggerTime} samples\n'
          f'\t- Gain: {Parameters.gain}')
    
    df = df.drop(columns=['Trigger_type','Frame_number'],errors='ignore')
    
    if 'snippets' in df.columns:
        df = explode_dataframe(df)
    
    tmp = df['PulseWaveform'].apply(pf.pulse_operations)

    columns = ['AreaOverHeightPass', 'MaximumIndex', 'PulseHeight', 'PulseWidth', 'PulseAreaADCC',
               'PulseStart', 'PulseEnd', 'BaselineADCC']
    for i, col in enumerate(columns):
        df[col] = [row[i] for row in tmp]
    df = df.explode(columns).reset_index(drop=True)
    df['PulseWaveform'] = df['PulseWaveform'] - df['BaselineADCC']
    
    floats = ['PulseAreaADCC', 'BaselineADCC', 'PulseHeight']
    bools = ['AreaOverHeightPass']
    integers = [c for c in columns if c not in [*floats,*bools]]
    df= df.astype({f:float for f in floats})
    df= df.astype({b:bool for b in bools})
    df= df.astype({i:int for i in integers})

    if data_parser.VERSION == 1:
        df.loc[:, 'Type'] = df.Type.astype('str')
        df.loc[:, 'Rest'] = df.Rest.astype('str')

    df['ApproxEnergy_keVee'] = df.apply(lambda x: pf.energyConversion(
        x['PulseAreaADCC'], x['Channel_number'], Parameters.gain), axis=1)

    df['PulseTime_us'] = df.apply(lambda x: pf.getRelativeTimeSnippets(
        x['Subsecs'], x['Timedelta_samples'], TimeWindow, PostTriggerTime, x['Channel_number']), axis=1)
    df = df.drop(columns=['Seconds','Subsecs','Timedelta_samples'],errors='ignore')
    # df['deltaT_us_CFD'] = df.apply(pf.computeTimeWithCFD,axis=1)
    # df['BoxcarSum'] = df.apply(lambda x: pf.getBoxcarSum(x.PulseWaveform,x.BaselineADCC),axis=1)

    df['preprocessingFlags'] = df.apply(lambda x: pf.getFlagsCorruptedData(x.Channel_number,x.PulseWaveform,x.Timestamp_s),axis=1)

    events = set(df.Event_ID)
    df = findDuplicateEvents(df)

    # dropping completely the datetime column until the bug in data_parser.data_io is corrected
    df = df.drop(columns=['Snippet_count','Snippet_index','Datetime'],errors='ignore')
    
    diffEvents = max(events) - min(events) + 1
    df['Event_ID'] = reorderEventIDs(df['Event_ID']) 
    df.attrs['missing_events_fraction']= 1 - len(events) / diffEvents
    df.attrs['duplicated_events_fraction'] = len(set(df.Event_ID[df.duplicateEvent==True])) / len(events)
    df = df.sort_values(['Event_ID','PulseTime_us']).reset_index(drop=True)

    return df

def cleanupDataframe(df):
    df = df[(df['preprocessingFlags'] == '') & (df['AreaOverHeightPass'] == True)]
    tmp = df.groupby('Event_ID')
    for (event_ID), event_DF in tmp:
        if len(event_DF.index) < event_DF['snippet_space'].iloc[0]:
            df.loc[df['Event_ID'] == event_ID,
                   'snippet_space'] = len(event_DF.index)
            df.loc[df['Event_ID'] == event_ID, 'Snippet_index'] = range(
                1, len(event_DF.index)+1)

    df = df.sort_values(['Event_ID', 'Snippet_index']).reset_index(drop=True)
    
    return df

def flattenSamples(PulseWaveform):
    return [x for xs in PulseWaveform for x in xs]

def df_to_root_file(df: pd.DataFrame, out_dir: str, namefile: str, mode: Literal['snippet','compact'] = 'compact', reduced = False) -> "list[uproot.writing.writable.WritableDirectory]":
    '''
    It creates the root file using the dataframe. It creates automatically the folder.
    If the mode is snippet, the function expects an exploded dataframe (i.e. each row is a pulse), 
    otherwise it expect each row is an event. In the last case it drops the column of the samples and of the preprocessing flags. To handle large datasets, it's recommended to use TChain and wildcards.
    '''
    df = df.sort_values(['Event_ID','PulseTime_us']).reset_index(drop=True)
    df_output = df

    if (mode == 'compact') and ('compact' not in df.attrs):
        df_output = compactDataframe(df_output)
    if reduced == True:
        df_output = reduceDataframe(df_output)
    
    df_output = df_output.drop(columns=['trigger_IDs','EventFlag'], errors='ignore')
    df['corruptedEvent'] = [d != '' for d in df.preprocessingFlags ]

    if 'compact' in df_output.attrs and df_output.attrs['compact'] == True:
        if 'PulseWaveform' in df_output:
            df_output['PulseWaveform'] = df_output.apply(lambda x: flattenSamples(x['PulseWaveform']),axis=1)
        df_output = df_output.drop(columns=['preprocessingFlags'], errors='ignore')
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    max_events = int(3e5)
    list_of_files = []
    
    pars = df.attrs
    for p in pars:
        pars[p] = [pars[p]]
    for i in range(36):
        if f'Threshold[{i}]' in pars:
            pars[f'Threshold_{i}'] = pars.pop(f'Threshold[{i}]')
    chunks = len(set(df.Event_ID)) // max_events +1
    for i in range(chunks):
        file = uproot.recreate(out / f'{namefile}_{i}.root')
        df_tmp = df_output[(df_output.Event_ID >= int(min(df_output.Event_ID)+i*max_events)) & (df_output.Event_ID < int(min(df_output.Event_ID)+(i+1)*max_events))].reset_index(drop=True)
        file['eventsTree'] = df_tmp
        if pars != {}:
            file['infoTree'] = pars
        # file['eventsTree'].show()
        list_of_files.append(file)
        file.close()

    return list_of_files

def make_total_dataFrame_processed(files: list|str) -> pd.DataFrame:

    if not isinstance(files, list):
        files = [files]
    df= pd.concat(
        load_files_to_df(files),
        ignore_index=True
    )
    metadata = getParametersFromJson(files)
    
    preprocessed_df=preprocessDataframe(df,TimeWindow=metadata['TimeWindow'],PostTriggerTime=metadata['PostTriggerTime'])

    getAdditionalParameters(preprocessed_df,metadata)
    
    preprocessed_df.attrs = metadata
    df.attrs = metadata

    return df, preprocessed_df
    
def convertDataframeToJson(df):
    '''
    This function is used exclusively in make_total_rootfile to get a json from a dataframe that stores
    metadata about each dataset
    '''
    metadata_dict = {}
    columns_to_average_snippets=['pulse_detection_efficiency', 'corrupted_snippets_fraction', 'snippets_wrong_timestamp_fraction']
    columns_to_average_events=['missing_events_fraction', 'duplicated_events_fraction']
    columns_to_sum = ['n_snippets','n_events','event_rate','snippet_rate']
    columns_only_first = [c for c in df.columns if c not in [*columns_to_average_snippets,*columns_to_average_events,*columns_to_sum]]
    
    for c in columns_only_first:
        metadata_dict[c] = int(df[c].agg(lambda x: x.value_counts().index[0]))
    for c in columns_to_average_events:
        metadata_dict[c] = float(np.average(df[c],weights=df['n_events']))
    for c in columns_to_average_snippets:
        metadata_dict[c] = float(np.average(df[c],weights=df['n_snippets']))
    for c in columns_to_sum:
        if c in ['n_snippets','n_events']:
            metadata_dict[c] = int(df[c].agg(sum))
        else:
            metadata_dict[c] = float(df[c].agg(sum))


    return metadata_dict

def wrapper_make_total_rootfile(files:list|str,out_dir: str,namefile_output: str, mode : Literal['snippet','compact'] = 'compact', reduced = False) -> dict:
    '''
    This is a wrapper of make_total_rootfile to be used to parallelize preprocessing
    '''
    _, preprocessed_df = make_total_dataFrame_processed(files)

    if reduced == True:
        preprocessed_df = reduceDataframe(preprocessed_df)

    _ = df_to_root_file(preprocessed_df,out_dir,namefile_output,mode=mode, reduced=reduced)

    preprocessed_df.to_pickle(f'{out_dir}/{namefile_output}.pickle')

    return preprocessed_df.attrs

def make_total_rootfile(files:list|str,out_dir: str,namefile_output: str, mode : Literal['snippet','compact'] = 'compact', reduced = False, parallel = False, n_jobs = 4) -> list | dict:
    '''
    Function to generate ROOT and pickle files from datasets. For large datasets, it is recommended to use
    the parallel function that doesn't return the dataframes. The compact mode is used to output a root file where each entry is an event, in the snippet mode each entry is a pulse. Use the reduced mode to remove 
    unnecessary columns. Note: in the parallel mode not all the metadata in df.attrs aren't reliable because in some cases they must be averaged over the number of snippets or events.
    '''

    if not isinstance(files,list):
        files = [files] 

    if parallel == True:  

        dicts_metadata = Parallel(n_jobs= n_jobs,verbose=10)(delayed(wrapper_make_total_rootfile)(files[i],out_dir, f'{namefile_output}_{i}',mode=mode,reduced=reduced) for i in range(len(files)))
        df_metadata = pd.DataFrame(dicts_metadata)
        metadata = convertDataframeToJson(df_metadata) 

        with open(f'{out_dir}/{namefile_output}.json','w+') as f:
            json.dump(metadata,f,indent=4)
        
        return metadata

    else:
        df, preprocessed_df = make_total_dataFrame_processed(files)

        root_files = df_to_root_file(preprocessed_df,out_dir,namefile_output,mode=mode, reduced=reduced)
        if reduced == True:
            preprocessed_df = reduceDataframe(preprocessed_df)

        preprocessed_df.to_pickle(f'{out_dir}/{namefile_output}.pickle')

        with open(f'{out_dir}/{namefile_output}.json','w+') as f:
            json.dump(preprocessed_df.attrs,f,indent=4)
    
        return df, preprocessed_df, root_files   
    
def explode_dataframe(df):
    dfc=df.explode('snippets').reset_index(drop=True)
    df=dfc.join(pd.json_normalize(dfc['snippets'])).drop(columns='snippets')
    return df

def compactDataframe(df):
    columns = ['AreaOverHeightPass', 'MaximumIndex', 'PulseHeight', 'PulseWidth', 'PulseAreaADCC',
               'PulseStart', 'PulseEnd', 'BaselineADCC', 'Channel_number', 'BoxcarSum', 'Timedelta_samples',
               'Snippet_index', 'min', 'max', 'PulseWaveform', 'ApproxEnergy_keVee', 'PulseTime_us',
               'preprocessingFlags', 'trigger_IDs']
    tmp=df.groupby('Event_ID')[[c for c in columns if c in df.columns]].agg(list).reset_index(drop=True)
    tmp2 = df.groupby('Event_ID')[[c for c in df.columns if c not in columns and c in df.columns]].agg('first').reset_index(drop=True)
    out = pd.concat([tmp2,tmp],axis=1)
    out.attrs = df.attrs
    out.attrs['compact']=True
    return out

def reduceDataframe(df):
    columns = ['Timedelta_samples', 'BoxcarSum', 'min', 'max', 'trigger_IDs', 'Trigger_type','Frame_number', 'Subsecs', 'Seconds',  'length', 'snippet_space', 'Datetime', 'EventFlag', 'trigger_count']
    df=df.drop(columns=columns, errors = 'ignore')
    return df

def getParametersFromJson(files: list|str):
    '''
    It derives the metadata from the json created after the generation of the bin file 
    and it replaces the unknown registers with default metadata
    '''
    if isinstance(files,str):
        files = [files]
    input_json=[f'{f.split(".")[0]}_results.{f.split(".")[1]}.json' for f in files]
    input_json = list(set(input_json))
    metadata = {'total_time':0, 'EventCounter': [], 'ThresholdSum' : [], 'PostTriggerTime': [], 'TimeWindow': [], 'FilterSet.T_Time': [], 'FilterSet.BP_Time': [], 'FilterSet.BS_Time': []}
    for i in range(36):
        metadata[f'Threshold[{i}]'] = []
    try:
        for j in input_json:
            with open(j,"r") as file:
                info = json.load(file)
                metadata['total_time'] += info['reception_time']
                for p in metadata:
                    if p in info:
                        metadata[p].append(info[p])
    except:
        print('Warning: using PostTriggerTime and TimeWindow from default parameters')
        metadata['PostTriggerTime'] = Parameters.PostTriggerTime
        metadata['TimeWindow'] = Parameters.TimeWindow
        metadata['total_time'] = 1
    for p in metadata:
        if isinstance(metadata[p],list) and len(set(metadata[p]))==1:
            metadata[p]=metadata[p][0]
    return metadata

def findDuplicateEvents(df: pd.DataFrame):
    duplicate_events = []
    energies = df.BoxcarSum
    snippet_count = df.Snippet_count
    for i,e in enumerate(energies):
            if i>snippet_count.iloc[i] and e == energies.iloc[i-snippet_count.iloc[i]] and df.Event_ID.iloc[i] != df.Event_ID.iloc[i-snippet_count.iloc[i]] and e > 1000:
                        duplicate_events.append(df.Event_ID.iloc[i])
                        duplicate_events.append(df.Event_ID.iloc[i-snippet_count.iloc[i]])
        
    duplicate_events = set(duplicate_events)
    df['duplicateEvent'] = [e in duplicate_events for e in df.Event_ID]
    return df

def getAdditionalParameters(df,metadata):
    metadata['snippet_rate'] = len(df.index) / metadata['total_time']
    metadata['event_rate'] = len(set(df['Event_ID'])) / metadata['total_time']

    metadata['pulse_detection_efficiency'] = len(df[df.AreaOverHeightPass == True].index) / len(df.index)
    metadata['corrupted_snippets_fraction'] = len(df[df.preprocessingFlags != ""])/len(df.index)
    metadata['missing_events_fraction'] = df.attrs['missing_events_fraction']
    metadata['duplicated_events_fraction'] = df.attrs['duplicated_events_fraction']
    
    posttriggertime = metadata["PostTriggerTime"]
    if isinstance(posttriggertime,list):
        posttriggertime = Parameters.PostTriggerTime
    
    metadata['snippets_wrong_timestamp_fraction'] = len(df[(df.PulseTime_us< -posttriggertime*16e-3) | (df.PulseTime_us> posttriggertime*16e-3)]) / len(df)
    metadata['n_snippets'] = len(df.index)
    metadata['n_events'] = len(set(df.Event_ID))
    
    
                
