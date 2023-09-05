import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker as plticker

from collections.abc import Iterable
# from configuration import CONFIG
# import configuration #.CONFIG as CONFIG
from .configuration import CONFIG

# CONFIG = configuration.CONFIG



def _get_samples_data(entry, key="samples"):

    if isinstance(entry, pd.core.series.Series):
        # entry is a row OR a column of a DataFrame
        if key in entry:
            # is a row
            return [entry[key]]
        else:
            # is a column
            return entry.to_list()
    elif isinstance(entry, pd.core.frame.DataFrame):
        return entry[key].to_list()
    elif isinstance(entry, list):
        return [entry]


def plot_data(index, data, ax):
    ax.plot(index, data)

# ----------------------------------------------------------------------

# def _get_rows(rows):
#     if isinstance(rows, pd.core.frame.DataFrame):
#         return rows.itertuples(), rows.shape[0]


def _plot_row(row, ax_flags, ax_samples, color=None, xlim=None, minor_locator=10.0):
    x_array = range(len(row.samples))
    flags = [1 if i in row.trigger_IDs else 0 for i in x_array]

    if isinstance(xlim, Iterable):
        ax_flags.set_xlim(*xlim)
        ax_samples.set_xlim(*xlim)
    elif isinstance(xlim, (int, float)) and not isinstance(xlim, bool):
        ax_flags.set_xlim(xlim)
        ax_samples.set_xlim(xlim)

    ax_flags.plot(
        x_array,
        flags,
        # label=row.Event_ID,
        color=color, linewidth=1, alpha=0.7)
    ax_samples.plot(
        x_array,
        row.samples,
        label=row.Event_ID,
        color=color, linewidth=1, alpha=0.7)

    loc = plticker.MultipleLocator(base=minor_locator) # this locator puts ticks at regular intervals
    ax_samples.xaxis.set_minor_locator(loc)


def _plot_dataFrame(df, axs, cmap, xlim=None):
    # iterrows, nrows = _get_rows(rows)
    iterrows = df.reset_index().itertuples()
    nrows = df.shape[0]

    for row in iterrows:
        color = cmap(row.Index/nrows)
        _plot_row(row, axs[0], axs[1], color, xlim)

    # srange = (0, max(df["samples"].map(len)))
    srange = (min(df['Event_ID']), max(df['Event_ID']))

    suptitle = f"Plots of events {srange[0]}-{srange[1]}"
    title = ""

    return nrows, srange, title, suptitle


def _plot_series(series, axs, cmap, xlim=None):

    _plot_row(series, axs[0], axs[1], cmap(0), xlim)

    eid = series.Event_ID
    suptitle = f"Event {eid}"
    udp_str = f"UDP-Infos: Type {series['Type']}\n      # {series['Number']}\n      Rest {series['Rest']}"
    eve_str = f"Event-Infos: Energy {series['Energy']}\n        Multiplicity {series['Multiplicity']}\n       Time {series['Seconds']}.{series['Subsecs']}"
    sta_str = f"Trigger count: {series['trigger_count']}\n      Min {series['min']}\n       Max {series['max']}"
    title = ', '.join(
        f"{key}: {series[key]}" for key in series.keys()
        if key not in ["trigger_IDs", "samples", "Event_ID"]
        )

    return 1, (eid,eid), title, suptitle


# def plot_compare(*args, xlim=None):


def plot_rows(rows, xlim=None):

    fig, axs = plt.subplots(
        2,1,
        gridspec_kw={'height_ratios': [1, 3]},
        figsize=(7.2, 4.8)
        )
    cmap = plt.colormaps["copper"]  # See also: viridis, brg, winter, copper, plasma

    if isinstance(rows, pd.core.frame.DataFrame):
        nrows, srange, title, suptitle = _plot_dataFrame(rows, axs, cmap, xlim)
    elif isinstance(rows, pd.core.series.Series):
        nrows, srange, title, suptitle = _plot_series(rows, axs, cmap, xlim)
    # List of lists
    # List of samples
    else:
        raise TypeError(f"Invalid type to plot {type(rows)}")


    mappable = matplotlib.cm.ScalarMappable(
        norm=matplotlib.colors.Normalize(vmin=srange[0], vmax=srange[1]),
        cmap=cmap
        )


    if nrows > 10:
        # Large number of plots -> Show colormap
        plt.colorbar(mappable=mappable, ax = axs)
    else:
        fig.legend(loc="center right")


    # Flag plot
    axs[0].margins(x=0, y=0)
    axs[0].set_ylabel("Trigger Flags")

    # Samples plot
    axs[1].margins(x=0)
    axs[1].set_xlabel("Sample IDs")
    axs[1].set_ylabel("ADC Values")

    # Title
    fig.suptitle(suptitle)
    if title != "":
        axs[0].set_title(
            title,
            fontsize="small",
            y=1.05,
            )
    # fig.tight_layout()
    # plt.show()
    return fig




def plot_samples(entry, key="samples"):
    cmap = plt.colormaps["plasma"]

    data = _get_samples_data(entry, key=key)
    index = range(len(data[0]))

    fig, axs = plt.subplots(2,1)

    # Flag plot
    axs[0].set_ylabel("Trigger Flags")

    # Samples plot
    axs[1].set_xlabel("Sample IDs")
    axs[1].set_ylabel("ADC Values")

    for d in data:
        plot_data(index, d, axs[1])

    # fig.tight_layout()
    # plt.show()
    return fig


def plot_events(df: pd.DataFrame, **kwargs):
    from .dataFrame_helpers import group_by_events

    events = group_by_events(df)
    for (filename, event_ID), event_DF in events:
        lowest_peak = min(event_DF["max"])
        highest_peak = max(event_DF["max"])
        if highest_peak > 2*lowest_peak:
            kwargs["ylim"] = kwargs.get("ylim") or (None, lowest_peak*1.5)

        if "PeakFinding" in event_DF.columns:
            kwargs["xlim"] = None
            left_bases = []
            right_bases = []
            for i, row in event_DF.iterrows():
                if "left_bases" in row["PeakFinding"][1].keys():
                    left_bases.append(min(row["PeakFinding"][1]["left_bases"]))
                    right_bases.append(max(row["PeakFinding"][1]["right_bases"]))
            kwargs["xlim"] = kwargs.get("xlim") or (min(left_bases), max(right_bases))
        plot_rows(event_DF, **kwargs)
