""""
Methods to ease manipulation of DataFrames and displaying information.
"""
import pandas as pd

def print_df_properties(df: pd.DataFrame) -> None:
    print("DataFrame", df.shape)
    cols = df.columns
    print("Columns:", len(cols))
    print(cols)
    files = df.index.unique("File")
    print("Files:", len(files))
    print(files)

    return cols, files