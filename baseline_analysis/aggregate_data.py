"""
Aggregate data

Collect all PulseWaveform from the snippets.
"""
import pandas as pd



def strip_final_zero(PulseWaveform: list) -> list:
    if PulseWaveform[-1] == 0:
        PulseWaveform.pop(-1)
    return PulseWaveform

def concatenate(SamplesSeries: pd.Series) -> pd.Series:
     return pd.Series([e for list_ in SamplesSeries for e in list_])

def print_conc_stats(FullChain: pd.Series) -> None:
    # print("FullChain statistics:")
    print(FullChain.describe(percentiles=[]))

def remove_pulses(PulseWaveform, pulses=None):
    # def remove_with_dict():

    if isinstance(pulses, dict):
        pass
    elif isinstance(pulses, list):
        pass
    elif pulses is None:
        return PulseWaveform


def main(df: pd.DataFrame):

    if "PulseWaveform" not in df:
        raise ValueError("DataFrame does not contain samples column")

    SamplesSeries = df["PulseWaveform"].apply(strip_final_zero)

    FullChain = concatenate(SamplesSeries)
    print_conc_stats(FullChain)

    return SamplesSeries, FullChain


