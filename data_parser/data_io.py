import pandas as pd
# from . import struct_conversion
from .struct_conversion import DataFile
from ..preprocess_data import peak_finding_algorithms as pf



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
    # df["Datetime"] = pd.to_datetime(df["Timestamp_s"]),
    df["Datetime"] = df["Timestamp_s"].apply(pd.Timestamp)

    return df


def load_files_to_df(files: list) -> pd.DataFrame:
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

def make_total_rootfile(files:list|str,out_dir,namefile_output):

    df=make_total_dataFrame(files)
    pf.df_to_root_file(df,out_dir,namefile_output)

