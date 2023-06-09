import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
from collections.abc import Iterable
# from configuration import CONFIG
# import configuration #.CONFIG as CONFIG
from .configuration import CONFIG

# CONFIG = configuration.CONFIG



def _get_samples_data(entry):

    if isinstance(entry, pd.core.series.Series):
        # entry is a row OR a column of a DataFrame
        if "samples" in entry:
            # is a row
            return [entry["samples"]]
        else:
            # is a column
            return entry.to_list()
    elif isinstance(entry, pd.core.frame.DataFrame):
        return entry["samples"].to_list()
    elif isinstance(entry, list):
        return [entry]


def plot_data(index, data, ax):
    ax.plot(index, data)

# ----------------------------------------------------------------------

# def _get_rows(rows):
#     if isinstance(rows, pd.core.frame.DataFrame):
#         return rows.itertuples(), rows.shape[0]


def _plot_row(row, ax_flags, ax_samples, color=None, xlim=None):

    index = range(len(row.samples))
    flags = [1 if i in row.trigger_IDs else 0 for i in index]

    if isinstance(xlim, Iterable):
        ax_flags.set_xlim(*xlim)
        ax_samples.set_xlim(*xlim)
    elif isinstance(xlim, (int, float)) and not isinstance(xlim, bool):
        ax_flags.set_xlim(xlim)
        ax_samples.set_xlim(xlim)

    ax_flags.plot(
        index,
        flags,
        # label=row.Event_ID,
        color=color, linewidth=1, alpha=0.7)
    ax_samples.plot(
        index,
        row.samples,
        label=row.Event_ID,
        color=color, linewidth=1, alpha=0.7)


def _plot_dataFrame(df, axs, cmap, xlim=None):
    # iterrows, nrows = _get_rows(rows)
    iterrows = df.itertuples()
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




def plot_samples(entry):
    cmap = plt.colormaps["plasma"]

    data = _get_samples_data(entry)
    index = range(len(data[0]))

    fig, axs = plt.subplots(2,1)

    # Flag plot
    axs[0].set_ylabel("Trigger Flags")

    # Samples plot
    axs[1].set_xlabel("Sample IDs")
    axs[1].set_ylabel("ADC Values")

    for d in data:
        plot_data(index, d, axs[1])

    fig.tight_layout()
    plt.show()