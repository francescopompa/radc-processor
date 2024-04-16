import pandas as pd
# from . import struct_conversion
from .struct_conversion import DataFile
from preprocess_data import peak_finding_algorithms as pf
import json



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

def make_total_dataFrame_processed(files: list|str) -> pd.DataFrame:

    if not isinstance(files, list):
        files = [files]
    df= pd.concat(
        load_files_to_df(files),
        ignore_index=True
    )
    df_updated=pf.update_dataframe_with_pulses(df)

    return df, df_updated
    
def make_total_rootfile(files:list|str,out_dir: str,namefile_output: str):
    # to do: add json handling (input and output)
    if isinstance(files,str):
        files = [files]
    input_json=[f'{f.split(".")[0]}_results.{f.split(".")[1]}.json' for f in files]
    parameters = {'total_time':0, 'rate': 0, 'ThresholdSum' : [], 'PostTriggerTime': [], 'TimeWindow': [], 'FilterSet.T_Time': [], 'FilterSet.BP_Time': [], 'FilterSet.BS_Time': []}
    for i in range(36):
        parameters[f'Threshold[{i}]'] = []
    
    for j in input_json:
        with open(j,"r") as file:
            info = json.load(file)
            parameters['total_time'] += info['reception_time']
            for p in parameters:
                if p in info:
                    parameters[p].append(info[p])

    df=make_total_dataFrame(files)
    df = explode_dataframe(df)
    df_updated=pf.update_dataframe_with_pulses(df)
    parameters['rate'] = len(df_updated.index) / parameters['total_time']
    parameters['pulse_detection_efficiency'] = len(df_updated.index) / len(df.index)
    with open(f'{out_dir}/{namefile_output}.json','w') as f:
        json.dump(parameters,f,indent=4)
    root_file = pf.df_to_root_file(df_updated,out_dir,namefile_output)
    return df, df_updated, root_file

def explode_dataframe(df):
    dfc=df.explode('snippets').reset_index(drop=True)
    df=dfc.join(pd.json_normalize(dfc['snippets'])).drop(columns='snippets')
    return df

