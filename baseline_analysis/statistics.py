import pandas as pd


def rolling_boxcar(PulseWaveform: list, window: int, offset: int = -1) -> list:
    """
    Assume Boxcar uses last n samples:
        - offset=-1: including the _current_ one.
        - offset=0: only the n _preceding_ samples.
    """
    def yield_val(PulseWaveform, window):
        for i in range(len(PulseWaveform[window+offset:])):
        # for i,e in enumerate(PulseWaveform[window+offset:]):
            end = window+i #+offset+1
            if end > len(PulseWaveform):
                break
            # print(PulseWaveform[i:end], e, i, end)
            yield sum(PulseWaveform[i:end])
    return list(yield_val(PulseWaveform, window))



def rolling_boxcar_row(row: pd.DataFrame, window: int, offset: int = -1) -> list:
    """
    Apply rolling_boxcar to a row. Meant for use with "df.apply".
    """
    return rolling_boxcar(PulseWaveform=row["PulseWaveform"], window=window, offset=offset)