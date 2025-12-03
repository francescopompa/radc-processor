import data_parser
data_parser.init('v2')

import numpy as np
import pandas as pd
import awkward as ak
from data_parser.struct_conversion import DataFile
from data_parser import Parameters
from data_parser import pulseFunctions as pf
import json
import uproot
from pathlib import Path
from typing import Literal
from joblib import Parallel, delayed



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

    return df


def load_files_to_df(files: list):
    for file in files:
        if isinstance(file, DataFile):
            yield datafile_to_df(file)
        else:
            yield datafile_to_df(DataFile(file))


def make_total_dataFrame(files: list | str) -> pd.DataFrame:
    """
    Creates a dataframe from a list of files without any processing
    """
    if not isinstance(files, list):
        files = [files]

    return pd.concat(
        load_files_to_df(files),
        ignore_index=True
    )

def findAccidentalCoincidencesTriggerRegion(df):
    """
    This function finds the accidental coincidences in the trigger region.
    It returns a flag to indicate if there is an accidental coincidence in the trigger region.
    The parameters can be customized in data_parser.Parameters.
    """
    tmp = df[np.abs(df.PulseTime_us) < Parameters.limit_trigger_region_us]
    grouped_df = tmp.groupby('Event_ID')
    times_max = grouped_df['PulseTime_us'].agg('max') / 0.016
    times_min = grouped_df['PulseTime_us'].agg('min') / 0.016
    timediff = np.rint(times_max - times_min)

    df.loc[:, 'AccidentalCoincidenceFlag'] = False
    df.loc[df.Event_ID.isin(
        timediff[timediff > Parameters.max_distance_accidental_coincidence].index), 'AccidentalCoincidenceFlag'] = True
    
    

def reorderEventIDs(series):
    """
    It puts all the event IDs in consecutive order.
    """
    series = np.array(series)
    consecutive_list = pd.Series(index=range(len(series)))
    counter = series[0]
    consecutive_list[0] = counter
    for i in range(1, len(series)):
        if series[i] != series[i-1]:
            counter += 1
        consecutive_list[i] = counter

    return consecutive_list.astype(int)

def clusterClassification(times):
    '''
    Function to make a simple cluster classification based on the distance between pulses.
    To be used as in this example:
    df['Cluster'] = df.groupby('Event_ID')['PulseTime_us'].transform(clusterClassification)
    '''
    timediff = [1,*np.diff(times)]
    clusters = []
    counter = 0
    for t in timediff:
        if t > Parameters.max_distance_accidental_coincidence * 0.016: counter += 1
        clusters.append(counter)
    return clusters


def preprocessDataframe(df: pd.DataFrame, TimeWindow=Parameters.TimeWindow, PostTriggerTime=Parameters.PostTriggerTime) -> pd.DataFrame:
    '''
    It adds the columns with the pulses parameters to the dataframe and calculates other useful quantities, such as the energy in keV and the time of each pulse relative to the main trigger
    '''
    if 'snippets' in df.columns:
        df = explode_dataframe(df)

    df = df.drop(columns=['Trigger_type', 'Frame_number'], errors='ignore')

    df['PulseTime_us'] = df.apply(lambda x: pf.getRelativeTimeSnippets(
        x['Subsecs'], x['Timedelta_samples'], TimeWindow, PostTriggerTime, x['Channel_number']), axis=1)
    df = df.drop(columns=['Seconds', 'Subsecs',
                 'Timedelta_samples'], errors='ignore')

    df.attrs['corrupted_snippets_fraction'] = len(df[(np.abs(df['PulseTime_us']) > (
        PostTriggerTime * 16e-3)) | (~df['Channel_number'].isin(range(37)))]) / len(df)
    df = df[df['Channel_number'].isin(range(37))]
    df = df.reset_index(drop=True)

    df[['AveragePulsePass', 'RE', 'MaximumIndex', 'PulseHeight', 'PulseAreaADCC',
        'BaselineADCC', 'PulseFlag']] = df.apply(pf.getPulseQuantities, axis=1).tolist()
    df['PulseWaveform'] = df.apply(lambda row: np.subtract(
        row.PulseWaveform, row.BaselineADCC), axis=1)
    
    # df.loc[:, 'AreaOverHeightRatio'] = df.PulseAreaADCC / \
    #     (df.PulseHeight + 0.01)
    # df['AreaOverHeightPass'] = (df.AreaOverHeightRatio < Parameters.max_ratio_charge_height) & (
    #     df.AreaOverHeightRatio > Parameters.min_ratio_charge_height)
    # df = df.drop(columns='AreaOverHeightRatio')

    integers = ['MaximumIndex']
    floats = ['PulseAreaADCC', 'BaselineADCC', 'PulseHeight',
              'RE', 'PulseAreaADCC', 'BaselineADCC']
    bools = ['AveragePulsePass', 'PulsePileUpFlag']
    df = df.astype({f: float for f in floats})
    df = df.astype({b: bool for b in bools})
    df = df.astype({i: int for i in integers})

    if data_parser.VERSION == 1:
        df.loc[:, 'Type'] = df.Type.astype('str')
        df.loc[:, 'Rest'] = df.Rest.astype('str')

    df.loc[:,'ApproxEnergy_keVee'] = df.apply(lambda x: pf.energyConversion(
        x['PulseAreaADCC'], x['Channel_number'], x['PulseHeight'], Parameters.gain), axis=1)

    events = set(df.Event_ID)
    diffEvents = max(events) - min(events) + 1
    df = df.reset_index(drop=True)
    df.loc[:,'Event_ID'] = reorderEventIDs(df['Event_ID'])
    df.attrs['missing_events_fraction'] = 1 - len(events) / diffEvents

    df = df.sort_values(['Event_ID', 'PulseTime_us']).reset_index(drop=True)
    df = df[np.abs(df['PulseTime_us']) < (PostTriggerTime * 16e-3)]
    df = df.reset_index(drop=True)

    df = findDuplicatePulses(df, TimeWindow)
    df = findDuplicatePulses(df, TimeWindow)
    df.attrs['duplicated_pulses_fraction'] = len(
        df[df['DistanceDuplicatePulse'] != 0]) / len(df)
    df.loc[df['DistanceDuplicatePulse'] != 0, 'PulseFlag'] += 'd'
    df = df.drop(columns=['Snippet_index', 'BoxcarSum', 'Snippet_count',
                'trigger_IDs', 'PulsePileUpFlag'], errors='ignore')

    # findAccidentalCoincidencesTriggerRegion(df)

    df.loc[:,'PulseTime_us'] = np.round(df['PulseTime_us'],3)
    df = df.sort_values(['Event_ID', 'PulseTime_us']).reset_index(drop=True)

    return df


def flattenSamples(PulseWaveform):
    """
    Function to convert the 2d waveforms in a 1d array for root export.
    """
    flattend = []
    for xs in PulseWaveform:
        try:
            for x in xs:
                flattend.append(x)
        except:
            flattend = flattend+[xs]*64
            print("!!! Empty Sample Detected !!!")
    return flattend


def convertPulseFlagsToInt(flag):
    """
    It converts the pulse flags to a binary mask:
    - undershoot and normal pulses (u and n): 0
    - saturation (s): 10
    - duplicate (d): 100
    - tail/small pileup/noise (t): 1000
    - pileup (p): 10000
    """

    flag_int = 0
    for c in flag:
        flag_int += Parameters.flag_dictionary[c]
            
    return flag_int


def df_to_root_file(df: pd.DataFrame, out_dir: str, namefile: str, mode: Literal['snippet', 'compact'] = 'compact', reduced=False) -> "list[uproot.writing.writable.WritableDirectory]":
    '''
    It creates the root file using the dataframe. It creates automatically the folder.
    If the mode is snippet, the function expects an exploded dataframe (i.e. each row is a pulse), 
    otherwise it expect each row is an event. In the last case it drops the column of the samples and of the preprocessing flags. To handle large datasets, it's recommended to use TChain and wildcards.
    It detects automatically if ROOT is available in the environment: if so, it uses awkward to convert the dataframe to a ROOT file with STL vectors as columns.
    '''
    df = df.sort_values(['Event_ID', 'PulseTime_us']).reset_index(drop=True)
    df_output = df

    df_output.loc[:,'PulseFlag'] = df_output['PulseFlag'].apply(convertPulseFlagsToInt)

    if (mode == 'compact') and ('compact' not in df.attrs):
        df_output = compactDataframe(df_output)
    if reduced == True:
        df_output = reduceDataframe(df_output)

    if 'compact' in df_output.attrs and df_output.attrs['compact'] == True:
        if 'PulseWaveform' in df_output:
            df_output.loc[:,'PulseWaveform'] = df_output.apply(
                lambda x: flattenSamples(x['PulseWaveform']), axis=1)
        if 'samples' in df_output:
            df_output.loc[:,'samples'] = df_output.apply(
                lambda x: flattenSamples(x['samples']), axis=1)
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
    chunks = len(set(df.Event_ID)) // max_events + 1
    for i in range(chunks):
        df_tmp = df_output[(df_output.Event_ID >= int(min(df_output.Event_ID)+i*max_events)) & (
            df_output.Event_ID < int(min(df_output.Event_ID)+(i+1)*max_events))].reset_index(drop=True)

        try:
            import ROOT
            build_rootfile(df_tmp, pars, out_dir, namefile, i)
        except:
            build_rootfile_with_uproot(df_tmp, pars, out_dir, namefile, i)

        list_of_files.append(f'{out_dir}/{namefile}_{i}.root')

    return list_of_files


def build_rootfile(df_tmp, pars, out_dir, namefile, i):
    """
    It builds a ROOT file using awkward.
    """
    import ROOT
    opts = ROOT.RDF.RSnapshotOptions()
    opts.fMode = "UPDATE"
    columns = df_tmp.columns
    Dict = {column: ak.Array(df_tmp[column]) for column in columns}
    rdf = ak.to_rdataframe(Dict)
    rdf.Snapshot('events/events', f'{out_dir}/{namefile}_{i}.root')

    if pars != {}:
        Dictpars = {keys.replace(".", "_"): v for keys,
                    v in pars.items() if not v == [[]]}
        rdfpar = ak.to_rdataframe(Dictpars)
        rdfpar.Snapshot('metadata/pars',
                        f'{out_dir}/{namefile}_{i}.root', options=opts)


def build_rootfile_with_uproot(df_tmp, pars, out_dir, namefile, i):
    """
    It builds the rootfile using uproot. To be used if ROOT is not available in the environment.
    """

    file = uproot.recreate(f'{out_dir}/{namefile}_{i}.root')
    file['eventsTree'] = df_tmp
    if pars != {}:
        file['infoTree'] = pars


def make_total_dataFrame_processed(files: list | str) -> pd.DataFrame:
    """ 
    It processes the list of files and returns the unprocessed and processed dataframes and the root file.
    """

    if not isinstance(files, list):
        files = [files]
    df = pd.concat(
        load_files_to_df(files),
        ignore_index=True
    )
    metadata = getParametersFromJson(files)
    preprocessed_df = preprocessDataframe(
        df, TimeWindow=metadata['TimeWindow'], PostTriggerTime=metadata['PostTriggerTime'])
    if Parameters.add_old_columns:
        preprocessed_df = addColumnsDataframeOldNames(preprocessed_df)

    getAdditionalParameters(preprocessed_df, metadata)

    preprocessed_df.attrs = metadata
    df.attrs = metadata

    return df, preprocessed_df


def convertDataframeToJson(df: pd.DataFrame) -> dict:
    '''
    This function is used exclusively in make_total_rootfile to get a json from a dataframe that stores
    metadata about each dataset
    '''
    metadata_dict = {}
    columns_to_average_snippets = ['pulse_detection_efficiency', 'corrupted_snippets_fraction',
                                   'duplicated_pulses_fraction']
    columns_to_average_events = ['missing_events_fraction']
    columns_to_sum = ['n_snippets', 'n_events', 'event_rate', 'snippet_rate']
    columns_only_first = [c for c in df.columns if c not in [
        *columns_to_average_snippets, *columns_to_average_events, *columns_to_sum]]

    for c in columns_only_first:
        if df[c].dtype == 'int' or df[c].dtype == 'float':
            metadata_dict[c] = int(df[c].agg(lambda x: x.value_counts().index[0]))
        elif c == 'commit':
            metadata_dict[c] = df[c].agg(lambda x: x.value_counts().index[0])
        elif df[c].dtype == 'object':
            print(
                f'Warning: Entry in Column "{c}" of Metadata is empty. Continuing with next column')
            continue
    for c in columns_to_average_events:
        metadata_dict[c] = float(np.average(df[c], weights=df['n_events']))
    for c in columns_to_average_snippets:
        metadata_dict[c] = float(np.average(df[c], weights=df['n_snippets']))
    for c in columns_to_sum:
        if c in ['n_snippets', 'n_events']:
            metadata_dict[c] = int(df[c].agg('sum'))
        else:
            metadata_dict[c] = float(df[c].agg('sum'))

    return metadata_dict


def wrapper_make_total_rootfile(files: list | str, out_dir: str, namefile_output: str, mode: Literal['snippet', 'compact'] = 'compact', reduced=False) -> dict:
    '''
    This is a wrapper of make_total_rootfile to be used to parallelize preprocessing
    '''
    _, preprocessed_df = make_total_dataFrame_processed(files)

    if reduced == True:
        preprocessed_df = reduceDataframe(preprocessed_df)

    _ = df_to_root_file(preprocessed_df, out_dir,
                        namefile_output, mode=mode, reduced=reduced)

    preprocessed_df.to_pickle(f'{out_dir}/{namefile_output}.pickle')

    return preprocessed_df.attrs


def make_total_rootfile(files: list | str, out_dir: str, namefile_output: str, mode: Literal['snippet', 'compact'] = 'compact', reduced=False, parallel=False, n_jobs=4) -> list | dict:
    '''
    Function to generate ROOT and pickle files from datasets. For large datasets, it is recommended to use
    the parallel function that doesn't return the dataframes. The compact mode is used to output a root file where each entry is an event, in the snippet mode each entry is a pulse. Use the reduced mode to remove unnecessary columns. Note: in the parallel mode not all the metadata in df.attrs are reliable because in some cases they must be averaged over the number of snippets or events.
    '''

    if not isinstance(files, list):
        files = [files]

    if parallel == True:

        dicts_metadata = Parallel(n_jobs=n_jobs, verbose=10)(delayed(wrapper_make_total_rootfile)(
            files[i], out_dir, f'{namefile_output}_{i}', mode=mode, reduced=reduced) for i in range(len(files)))
        df_metadata = pd.DataFrame(dicts_metadata)
        metadata = convertDataframeToJson(df_metadata)

        with open(f'{out_dir}/{namefile_output}.json', 'w+') as f:
            json.dump(metadata, f, indent=4)

        return metadata

    else:
        df, preprocessed_df = make_total_dataFrame_processed(files)

        root_files = df_to_root_file(
            preprocessed_df, out_dir, namefile_output, mode=mode, reduced=reduced)
        if reduced == True:
            preprocessed_df = reduceDataframe(preprocessed_df)

        preprocessed_df.to_pickle(f'{out_dir}/{namefile_output}.pickle')

        with open(f'{out_dir}/{namefile_output}.json', 'w+') as f:
            json.dump(preprocessed_df.attrs, f, indent=4)

        return df, preprocessed_df, root_files
    

def readPickleFiles(files: list | str) -> pd.DataFrame:
    '''
    Function to read a list a pickle files. 
    The function handles the metadata and makes order in Event_IDs.
    It returns the data as a total dataframe.
    '''
    if not isinstance(files, list):
        files = [files]
    files.sort()
    list_of_dfs = []
    for f in files:
        df = pd.read_pickle(f)
        metadata = df.attrs
        list_of_dfs.append(df)

    df = pd.concat(list_of_dfs,ignore_index=True)
    df.attrs=metadata
    df = df.reset_index(drop=True)

    df.loc[:,'Event_ID'] = reorderEventIDs(df.Event_ID)
    df = df.sort_values(['Event_ID','PulseTime_us']).reset_index(drop=True)
    return df


def explode_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    It changes the structure of the unprocessed dataframe. The snippets column is a dictionary and it's converted to different columns corresponding to the keys of the dictionary.
    """
    dfc = df.explode('snippets').reset_index(drop=True)
    df = dfc.join(pd.json_normalize(dfc['snippets'])).drop(columns='snippets')
    return df


def compactDataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    It converts the entries in the same events to lists. To be used for ROOT export.
    """
    columns = ['AreaOverHeightPass', 'MaximumIndex', 'PulseHeight', 'PulseWidth', 'PulseAreaADCC',
               'PulseStart', 'PulseEnd', 'BaselineADCC', 'Channel_number', 'BoxcarSum', 'Timedelta_samples',
               'Snippet_index', 'min', 'max', 'PulseWaveform', 'ApproxEnergy_keVee', 'PulseTime_us',
               'preprocessingFlags', 'trigger_IDs', 'DistanceDuplicatePulse', 'RE', 'PulseFlag', 'AveragePulsePass', 'PulsePileUpFlag','Charge_keV','Charge','MaxIndex','deltaT_us','samples','IsPulse','Baseline'] 
    tmp = df.groupby('Event_ID')[[c for c in columns if c in df.columns]].agg(
        list).reset_index(drop=True)
    tmp2 = df.groupby('Event_ID')[[c for c in df.columns if c not in columns and c in df.columns]].agg(
        'first').reset_index(drop=True)
    out = pd.concat([tmp2, tmp], axis=1)
    out.attrs = df.attrs
    out.attrs['compact'] = True
    return out


def reduceDataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    It reduces the dataframe size by removing some useless columns. 
    """
    columns = ['Event_ID', 'Timestamp_s', 'Channel_number',
       'PulseTime_us', 'AveragePulsePass', 'PulseHeight', 'PulseAreaADCC',
       'PulseFlag', 'ApproxEnergy_keVee','DistanceDuplicatePulse']
    
    columns = [c for c in columns if c in df.columns]
    return df[columns]


def getParametersFromJson(files: list | str):
    '''
    It derives the metadata from the json created after the generation of the bin file 
    and it replaces the unknown registers with default metadata
    '''
    if isinstance(files, str):
        files = [files]
    input_json = [
        f'{f.split(".")[0]}_results.{f.split(".")[1]}.json' for f in files]
    input_json = list(set(input_json))
    metadata = {'total_time': 0, 'EventCounter': [], 'ThresholdSum': [], 'PostTriggerTime': [
    ], 'TimeWindow': [], 'FilterSet.T_Time': [], 'FilterSet.BP_Time': [], 'FilterSet.BS_Time': []}
    for i in range(36):
        metadata[f'Threshold[{i}]'] = []
    try:
        for j in input_json:
            with open(j, "r") as file:
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
        if isinstance(metadata[p], list) and len(set(metadata[p])) == 1:
            metadata[p] = metadata[p][0]
    return metadata


def findDuplicatePulses(df: pd.DataFrame, TimeWindow=Parameters.TimeWindow) -> pd.DataFrame:
    """
    This function finds all the duplicate pulses.
    If the pulses are in the same event, one is removed.
    If the pulses are in different events, the second in order of time is removed if it has a time difference to the first greater than the time window.
    """
    df['DistanceDuplicatePulse'] = 0
    for i in range(1, 20):
        condition = (df.PulseAreaADCC.shift(i) == df.PulseAreaADCC) & (
            df.BaselineADCC.shift(i) == df.BaselineADCC) & (df.Event_ID == df.Event_ID.shift(i))
        df = df.drop(df[condition].index)
    for i in range(500, 0, -1):
        condition = (df.PulseAreaADCC.shift(i) == df.PulseAreaADCC) & (df.BaselineADCC.shift(i) == df.BaselineADCC) & (
            df.Event_ID != df.Event_ID.shift(i)) & (df.Channel_number == df.Channel_number.shift(i))
        df.loc[condition, 'DistanceDuplicatePulse'] = -i
        df.loc[pd.Series(condition).shift(-i, fill_value=False),
               'DistanceDuplicatePulse'] = i
    df = df.reset_index(drop=True)
    df.loc[:, 'TimeDifference'] = df.apply(lambda x: (
        df['Timestamp_s'][x.name + x.DistanceDuplicatePulse]-df['Timestamp_s'][x.name])*1e6, axis=1)

    df = df[df.TimeDifference > -TimeWindow*16e-3]
    df = df.drop(columns='TimeDifference')
    df = df.reset_index(drop=True)
    for i in range(500, 0, -1):
        condition = (df.PulseAreaADCC.shift(i) == df.PulseAreaADCC) & (df.BaselineADCC.shift(i) == df.BaselineADCC) & (
            df.Event_ID != df.Event_ID.shift(i)) & (df.Channel_number == df.Channel_number.shift(i))
        df.loc[condition, 'DistanceDuplicatePulse'] = -i
        df.loc[pd.Series(condition).shift(-i, fill_value=False),
               'DistanceDuplicatePulse'] = i

    return df.reset_index(drop=True)


def getAdditionalParameters(df: pd.DataFrame, metadata: dict):
    metadata['snippet_rate'] = len(df) / metadata['total_time']
    metadata['event_rate'] = len(set(df['Event_ID'])) / metadata['total_time']

    metadata['pulse_detection_efficiency'] = len(
        df[df.AveragePulsePass]) / len(df)
    metadata['corrupted_snippets_fraction'] = df.attrs['corrupted_snippets_fraction']
    metadata['missing_events_fraction'] = df.attrs['missing_events_fraction']
    metadata['duplicated_pulses_fraction'] = df.attrs['duplicated_pulses_fraction']

    posttriggertime = metadata["PostTriggerTime"]
    if isinstance(posttriggertime, list):
        posttriggertime = Parameters.PostTriggerTime
    # metadata['AccidentalCoincidenceThreshold'] = Parameters.max_distance_accidental_coincidence
    metadata['n_snippets'] = len(df)
    metadata['n_events'] = len(set(df.Event_ID))
    metadata['commit'] = getCommit() 


def getCommit() -> str:
    base_path = Path(data_parser.__file__).parent.parent
    git_dir = Path(base_path) / '.git'
    with (git_dir / 'HEAD').open('r') as head:
        ref = head.readline().split(' ')[-1].strip()

    with (git_dir / ref).open('r') as git_hash:
        return git_hash.readline().strip()[:7]

def renameColumnsDataframe(df: pd.DataFrame) -> pd.DataFrame:
    '''
    This function creates copies of the columns, going from the old naming convention to the new one.
    '''
    df.loc[:,'ApproxEnergy_keVee'] = df.Charge_keV
    df.loc[:,'PulseEnd'] = df.EndPulse
    df.loc[:,'PulseStart'] = df.StartPulse
    df.loc[:,'PulseAreaADCC'] = df.Charge
    df.loc[:,'MaximumIndex'] = df.MaxIndex
    df.loc[:,'PulseTime_us'] = df.deltaT_us
    df.loc[:,'PulseWaveform'] = df.samples
    df.loc[:,'AreaOverHeightPass'] = df.IsPulse
    df.loc[:,'BaselineADCC'] = df.Baseline
    return df

def addColumnsDataframeOldNames(df: pd.DataFrame) -> pd.DataFrame:
    '''
    This function creates copies of the column of the dataframes with the old naming convention.
    '''
    df.loc[:,'Charge_keV'] = df.ApproxEnergy_keVee
    df.loc[:,'Charge'] = df.PulseAreaADCC
    df.loc[:,'MaxIndex'] = df.MaximumIndex
    df.loc[:,'deltaT_us'] = df.PulseTime_us
    df.loc[:,'samples'] = df.PulseWaveform
    df.loc[:,'IsPulse'] = df.AreaOverHeightPass
    df.loc[:,'Baseline'] = df.BaselineADCC
    df.loc[:,'Snippet_count'] = df.groupby('Event_ID')['Event_ID'].transform(len)
    df.loc[:,'Snippet_count'] = df.Snippet_count.astype(int)
    return df


