""""
Methods to ease manipulation of DataFrames and displaying information.
"""
import pandas as pd
import numpy as np

def print_df_properties(df: pd.DataFrame) -> None:
    print("DataFrame", df.shape)
    cols = df.columns
    print("Columns:", len(cols))
    print(cols)
    files = df.index.unique("File")
    print("Files:", len(files))
    print(files)
    print("Snippets", df.shape[0])
    for file in files:
        sub_df = df.loc[file]
        print(">", file)
        for channel in np.sort(sub_df["Channel_number"].unique()):
            print(f"  - Channel {channel:02}:", sub_df[sub_df["Channel_number"] == channel].shape[0])

    return cols, files


def group_by_events(df: pd.DataFrame) -> pd.core.groupby.DataFrameGroupBy:
    return df.groupby(["File", "Event_ID"])

