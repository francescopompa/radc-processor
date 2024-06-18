import data_parser
data_parser.init('v2')
import numpy as np
import pandas as pd
# from . import struct_conversion
from .struct_conversion import DataFile
from preprocess_data import Parameters
from preprocess_data import peak_finding_algorithms as pf
import json
import uproot
from pathlib import Path




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

def preprocessDataframe(df: pd.DataFrame, TimeWindow = Parameters.TimeWindow, PostTriggerTime = Parameters.PostTriggerTime) -> pd.DataFrame:
    '''
    It adds the columns with the pulses parameters to the dataframe
    '''
    if 'snippets' in df.columns:
        df = explode_dataframe(df)
    tmp = df['samples'].apply(pf.pulse_operations)

    columns = ['IsPulse', 'MaxIndex', 'PulseHeight', 'PulseWidth', 'Charge',
               'StartPulse', 'EndPulse', 'Baseline']
    for i, col in enumerate(columns):
        df[col] = [row[i] for row in tmp]
    df = df.explode(['IsPulse', 'MaxIndex', 'PulseHeight', 'PulseWidth', 'Charge',
                     'StartPulse', 'EndPulse', 'Baseline']).reset_index(drop=True)

    if data_parser.VERSION == 1:
        df.loc[:, 'Type'] = df.Type.astype('str')
        df.loc[:, 'Rest'] = df.Rest.astype('str')

    df['Charge_keV'] = df.apply(lambda x: pf.energyConversion(
        x['Charge'], x['Channel_number'], Parameters.gain), axis=1)
    df['deltaT_us'] = df.apply(lambda x: pf.getRelativeTimeSnippets(
        x['Subsecs'], x['Timedelta_samples'], TimeWindow, PostTriggerTime), axis=1)
    df['BoxcarSum'] = df.apply(lambda x: pf.getBoxcarSum(x.samples,x.Baseline),axis=1)

    df['preprocessingFlags']= df.apply(lambda x: pf.getFlagsCorruptedData(x.Channel_number,x.samples,x.Timestamp_s),axis=1)

    df['samples'] = [s if (isinstance(s,list) and (len(s) == 64)) else list(np.zeros(64)) for s in df.samples]

    df.loc[:, 'Datetime'] = df['Datetime'].dt.strftime('%Y%m%d')
    df.loc[:, 'Datetime'] = df.Datetime.astype('int64')

    events = set(df.Event_ID)
    counter = 0
    for e in range(max(events)):
        if e not in events:
            counter += 1
    df.loc[:,'missing_events_fraction']=counter/len(events)
    df = removeDuplicateEvents(df)
    df['Event_ID'] = df['Event_ID'].rank(method='dense').astype(int) 
    n_events_unique = len(set(df.Event_ID))
    df.loc[:,'duplicated_events_fraction'] = 1 - n_events_unique / len(events)

    return df

def cleanupDataframe(df):
    df = df[(df['preprocessingFlags'] == '') & (df['IsPulse'] == True)]
    tmp = df.groupby('Event_ID')
    for (event_ID), event_DF in tmp:
        if len(event_DF.index) < event_DF['snippet_space'].iloc[0]:
            df.loc[df['Event_ID'] == event_ID,
                   'snippet_space'] = len(event_DF.index)
            df.loc[df['Event_ID'] == event_ID, 'Snippet_number'] = range(
                1, len(event_DF.index)+1)

    df = df.sort_values(['Event_ID', 'Snippet_number'])
    
    return df


def df_to_root_file(df: pd.DataFrame, out_dir: str, namefile: str) -> uproot.writing.writable.WritableDirectory:
    '''
    It creates the root file using the dataframe. Attention: it creates automatically the folder
    '''
    if 'trigger_IDs' in df.columns:
        df = df.drop(columns='trigger_IDs')
    if 'Info_flags' in df.columns:
        df = df.drop(columns='Info_flags')
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    file = uproot.recreate(out / (namefile + ".root"))
    file['eventsTree'] = df
    return file

def make_total_dataFrame_processed(files: list|str) -> pd.DataFrame:

    if not isinstance(files, list):
        files = [files]
    df= pd.concat(
        load_files_to_df(files),
        ignore_index=True
    )
    parameters = getParametersFromJson(files)
    
    df_updated=preprocessDataframe(df,TimeWindow=parameters['TimeWindow'],PostTriggerTime=parameters['PostTriggerTime'])

    getAdditionalParameters(df_updated,parameters)
    
    df_updated.attrs = parameters
    df.attrs = parameters


    return df, df_updated
    
def make_total_rootfile(files:list|str,out_dir: str,namefile_output: str):
    
    if isinstance(files,str):
        files = [files]
    
    df = make_total_dataFrame(files)
    df = explode_dataframe(df)
    parameters = getParametersFromJson(files)

    df_updated = preprocessDataframe(df,TimeWindow = parameters['TimeWindow'], PostTriggerTime= parameters['PostTriggerTime'])

    getAdditionalParameters(df_updated,parameters)

    df.attrs = parameters
    df_updated.attrs = parameters

    root_file = df_to_root_file(df_updated,out_dir,namefile_output)
    with open(f'{out_dir}{namefile_output}.json','w+') as f:
        json.dump(parameters,f,indent=4)
    for p in parameters:
        parameters[p] = [parameters[p]]
    root_file['infoTree'] = parameters
    
    return df, df_updated, root_file

def explode_dataframe(df):
    dfc=df.explode('snippets').reset_index(drop=True)
    df=dfc.join(pd.json_normalize(dfc['snippets'])).drop(columns='snippets')
    return df

def getParametersFromJson(files: list|str):
    '''
    It derives the parameters from the json created after the generation of the bin file 
    and it replaces the unknown registers with default parameters
    '''
    if isinstance(files,str):
        files = [files]
    # replace this with a function to cover the case of chunks
    input_json=[f'{f.split(".")[0]}_results.{f.split(".")[1]}.json' for f in files]
    parameters = {'total_time':0, 'EventCounter': [], 'ThresholdSum' : [], 'PostTriggerTime': [], 'TimeWindow': [], 'FilterSet.T_Time': [], 'FilterSet.BP_Time': [], 'FilterSet.BS_Time': []}
    for i in range(36):
        parameters[f'Threshold[{i}]'] = []
    try:
        for j in input_json:
            with open(j,"r") as file:
                info = json.load(file)
                parameters['total_time'] += info['reception_time']
                for p in parameters:
                    if p in info:
                        parameters[p].append(info[p])
    except:
        print('Warning: using PostTriggerTime and TimeWindow from default parameters')
        parameters['PostTriggerTime'] = Parameters.PostTriggerTime
        parameters['TimeWindow'] = Parameters.TimeWindow
        parameters['total_time'] = 1
    for p in parameters:
        if isinstance(parameters[p],list) and len(set(parameters[p]))==1:
            parameters[p]=parameters[p][0]
    return parameters

def removeDuplicateEvents(df: pd.DataFrame):
    duplicate_events = []
    energies = df.Energy
    snippet_count = df.Snippet_count
    for i,e in enumerate(energies):
            if i>snippet_count.iloc[i]:
                if e == energies.iloc[i-snippet_count.iloc[i]]:
                    if snippet_count.iloc[i] <= snippet_count.iloc[i-snippet_count.iloc[i]]: 
                        duplicate_events.append(df.Event_ID.iloc[i])
                    else:
                        duplicate_events.append(df.Event_ID.iloc[i-snippet_count[i]])
    
    duplicate_events = set(duplicate_events)
    df['condition'] = [d not in duplicate_events for d in df.Event_ID]
    df.drop(df[df['condition'] == False].index, inplace=True)
    df.drop(columns='condition', inplace=True)
    df = df.reset_index(drop = True)
    return df

def getAdditionalParameters(df,parameters):
    parameters['snippet_rate'] = len(df.index) / parameters['total_time']
    parameters['event_rate'] = len(set(df['Event_ID'])) / parameters['total_time']

    parameters['pulse_detection_efficiency'] = len(df[df.IsPulse == True].index) / len(df.index)
    parameters['corrupted_snippets_fraction'] = len(df[df.preprocessingFlags != ""])/len(df.index)
    parameters['missing_events_fraction'] = df['missing_events_fraction'].iloc[0]
    parameters['duplicated_events_fraction'] = df['duplicated_events_fraction'].iloc[0]
    df.drop(columns = ['missing_events_fraction','duplicated_events_fraction'],inplace = True)
    
    
                
