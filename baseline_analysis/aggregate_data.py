"""
Aggregate data

Collect all samples from the snippets.
"""
import pandas as pd



def strip_final_zero(samples: list) -> list:
    if samples[-1] == 0:
        samples.pop(-1)
    return samples

def concatenate(SamplesSeries: pd.Series) -> pd.Series:
     return pd.Series([e for list_ in SamplesSeries for e in list_])

def print_conc_stats(FullChain: pd.Series) -> None:
    # print("FullChain statistics:")
    print(FullChain.describe(percentiles=[]))

def remove_pulses(samples, pulses=None):
    # def remove_with_dict():

    if isinstance(pulses, dict):
        pass
    elif isinstance(pulses, list):
        pass
    elif pulses is None:
        return samples


def main(df: pd.DataFrame):

    if "samples" not in df:
        raise ValueError("DataFrame does not contain samples column")

    SamplesSeries = df["samples"].apply(strip_final_zero)

    FullChain = concatenate(SamplesSeries)
    print_conc_stats(FullChain)

    return SamplesSeries, FullChain


