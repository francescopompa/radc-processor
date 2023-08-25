import pandas as pd


def rolling_boxcar(samples: list, window: int, offset: int = -1) -> list:
    """
    Assume Boxcar uses last n samples:
        - offset=-1: including the _current_ one.
        - offset=0: only the n _preceding_ samples.
    """
    def yield_val(samples, window):
        for i in range(len(samples[window+offset:])):
        # for i,e in enumerate(samples[window+offset:]):
            end = window+i #+offset+1
            if end > len(samples):
                break
            # print(samples[i:end], e, i, end)
            yield sum(samples[i:end])
    return list(yield_val(samples, window))



def rolling_boxcar_row(row: pd.DataFrame, window: int, offset: int = -1) -> list:
    """
    Apply rolling_boxcar to a row. Meant for use with "df.apply".
    """
    return rolling_boxcar(samples=row["samples"], window=window, offset=offset)