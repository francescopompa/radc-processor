import pandas as pd
from .struct_conversion import DataFile



def datafile_to_df(file):

    return pd.DataFrame.from_records(
        file.get_records(),
        index=None,
        exclude=None,
        columns=None,
    )


def load_files_to_df(files):
    for file in files:
        if isinstance(file, DataFile):
            yield datafile_to_df(file)
        else:
            yield datafile_to_df(DataFile(file))


def make_total_dataFrame(files):

    if not isinstance(files, list):
        files = [files]

    return pd.concat(
        load_files_to_df(files),
        ignore_index=True
        )
