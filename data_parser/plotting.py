import pandas as pd
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker as plticker

from collections.abc import Iterable
# from configuration import CONFIG
# import configuration #.CONFIG as CONFIG
from .configuration import CONFIG
from pathlib import Path
import numpy as np
from preprocess_data.peak_finding_algorithms import getRelativeTimeSnippets

# CONFIG = configuration.CONFIG
CONVERSIONS = {
    "time_ns": {
        "from_adc": 16,
        "to_adc": 1/16
    },
    "voltage_mv": {
        #
        # Todo: replace with fitted values?
        #
        "from_adc": 2000/2**14,
        "to_adc": 2**14/2000
    }
}

def convert_adc_ns(adc: Iterable|int) -> Iterable|int:
    factor = CONVERSIONS["time_ns"]["from_adc"]
    if isinstance(adc, Iterable):
        return (e*factor for e in adc)
    else:
        return adc*factor

def convert_adc_mV(adc: Iterable|int) -> Iterable|int:
    #
    # Todo: replace with axis-rescale method?
    #
    factor = CONVERSIONS["voltage_mv"]["from_adc"]
    if isinstance(adc, Iterable):
        return (e*factor for e in adc)
    else:
        return adc*factor

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


def _plot_row(row, ax_flags, ax_samples, **kwargs):
    #
    # Todo: plot points above 8192-1 in other color/mark them
    #
    # color = kwargs.get("color")
    # minor_locator = kwargs.get("minor_locator") or 10.0
    color = kwargs.pop("color")
    minor_locator = kwargs.pop("minor_locator", 10.0)# or 10.0

    x_array = range(len(row.samples))
    flags = [1 if i in row.trigger_IDs else 0 for i in x_array]

    ax_flags.plot(
        x_array,
        flags,
        # label=row.Event_ID,
        color=color, linewidth=1, alpha=0.7)
    ax_samples.plot(
        x_array,
        row.samples,
        label=row.Event_ID,
        color=color, linewidth=1, alpha=0.7,
        **kwargs)

    loc = plticker.MultipleLocator(base=minor_locator) # this locator puts ticks at regular intervals
    ax_samples.xaxis.set_minor_locator(loc)


def _plot_dataFrame(df, ax_flags, ax_samples, cmap, **kwargs):
    # iterrows, nrows = _get_rows(rows)
    iterrows = df.reset_index().itertuples()
    nrows = df.shape[0]

    if nrows == 0:
        return

    for row in iterrows:
        color = cmap(row.Index/nrows)
        _plot_row(row, ax_flags, ax_samples, color=color, **kwargs)

    # srange = (0, max(df["samples"].map(len)))
    srange = (min(df['Event_ID']), max(df['Event_ID']))
    crange = sorted(df["Channel_number"].unique())

    suptitle = f"Plots of events {srange[0]}-{srange[1]}"
    suptitle += f"\nChannels {crange}"

    title = kwargs.get("title") or ""

    return nrows, srange, title, suptitle


def _plot_series(series, ax_flags, ax_samples, cmap, **kwargs):

    _plot_row(series, ax_flags, ax_samples, color=cmap(0), **kwargs)

    eid = series.Event_ID
    suptitle = kwargs.get("suptitle") or f"Event {eid}"
    udp_str = f"UDP-Infos: Type {series['Type']}, # {series['Number']}, Rest {series['Rest']}"
    eve_str = f"Event-Infos: Energy {series['Energy']}, Multiplicity {series['Multiplicity']}, Time {series['Seconds']}.{series['Subsecs']}"
    sta_str = f"Trigger count: {series['trigger_count']}, Min {series['min']}, Max {series['max']}"
    # title = kwargs.get("title") or ', '.join(
    #     f"{key}: {series[key]}" for key in series.keys()
    #     if key not in ["trigger_IDs", "samples", "Event_ID"]
    #     )
    title = kwargs.get("title") or ' '.join(
        [udp_str, eve_str, sta_str]
        )

    return 1, (eid,eid), title, suptitle


# def plot_compare(*args, xlim=None):


def plot_rows(rows, **kwargs):
    # https://stackoverflow.com/questions/37725462/how-can-i-rescale-axis-without-scaling-the-image-in-an-image-plot-with-matplotli
    # https://stackoverflow.com/questions/30883933/matplotlib-rescale-axis-labels
    # https://stackoverflow.com/questions/68847226/how-to-rescale-an-axis-with-matplotlib
    #
    #

    fig, (ax_flags, ax_samples) = plt.subplots(
        2,1,
        gridspec_kw={'height_ratios': [1, 3]},
        figsize=(7.2, 4.8)
        )
    cmap = plt.colormaps["copper"]  # See also: viridis, brg, winter, copper, plasma

    xlim = kwargs.pop("xlim", None)
    ylim = kwargs.pop("ylim", None)
    if xlim: ax_flags.set_xlim(xlim)
    if xlim: ax_samples.set_xlim(xlim)
    if ylim: ax_samples.set_ylim(ylim)

    if isinstance(rows, pd.core.frame.DataFrame):
        nrows, srange, title, suptitle = _plot_dataFrame(rows, ax_flags, ax_samples, cmap, **kwargs)
    elif isinstance(rows, pd.core.series.Series):
        # It's a single row
        nrows, srange, title, suptitle = _plot_series(rows, ax_flags, ax_samples, cmap, **kwargs)
    # List of lists
    # Series of lists (column)
    # List of samples (single entry)
    else:
        raise TypeError(f"Invalid type to plot {type(rows)}")


    mappable = matplotlib.cm.ScalarMappable(
        norm=matplotlib.colors.Normalize(vmin=srange[0], vmax=srange[1]),
        cmap=cmap
        )


    if nrows > 10:
        # Large number of plots -> Show colormap
        plt.colorbar(mappable=mappable, ax = (ax_flags, ax_samples))
    else:
        fig.legend(loc="center right")


    # Flag plot
    ax_flags.margins(x=0, y=0)
    ax_flags.set_ylabel("Trigger Flags")

    # Samples plot
    ax_samples.margins(x=0)
    ax_samples.set_xlabel("Sample IDs")
    ax_samples.set_ylabel("ADC Values")

    # Title
    fig.suptitle(suptitle)
    if title != "":
        ax_flags.set_title(
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
    for (event_ID), event_DF in events:
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

def plot_events_coincidence(df: pd.DataFrame, timeWindow= 12500, n_events = 50, save = False, outDir = "./images"):
    from .dataFrame_helpers import group_by_events
    # plt.rcParams["axes.prop_cycle"] = plt.cycler("color", plt.cm.tab20c.colors)
    if save == True:
        p = Path(outDir)
        p.mkdir(parents=True, exist_ok=True)
    events = group_by_events(df)
    counter =0
    for (event_ID), event_DF in events:
        counter += 1
        deltaT_samples = event_DF['Timedelta_samples']
        energies = event_DF['Energy']
        channels = event_DF['Channel_number']
        subsecs = event_DF['Subsecs'].iloc[0]
        if 'BoxcarSum' in event_DF.columns:
            energies2=event_DF['BoxcarSum']
        # to do 
        # find a way to convert to more informative energy units
        
        relativeTime=[getRelativeTimeSnippets(subsecs,d) for d in deltaT_samples]
       
        fig,ax=plt.subplots(ncols=1,nrows=2,layout='constrained')
        for i in range(len(event_DF.index)):
            ax[0].plot(event_DF['samples'].iloc[i],label=f'{i+1}: channel {channels.iloc[i]}')
            plot=ax[1].plot(relativeTime[i],energies.iloc[i],'o')
            color=plot[0].get_color()
            ax[1].vlines(relativeTime[i],0,energies.iloc[i],color=color)

            if 'BoxcarSum' in event_DF.columns:
                ax[1].plot(relativeTime[i],energies2.iloc[i],'o',color=color,alpha=0.5)

        ax[0].set_xlabel('Sample ID')
        ax[0].set_ylabel('ADC counts')
        ax[0].legend()
        #ax[1].set_xlim(-5,max(relativeTime)*1.2)
        ax[1].set_ylim(0,max((*energies,*energies2))*1.2)
        ax[1].set_xlabel(r'Time ($\mu$s)')
        ax[0].set_title(f'Event {event_ID[0]}')
        ax[1].set_ylabel('Boxcar energy (ADCC)')
        ax[1].set_box_aspect(1/5)
        # fig.tight_layout()
        plt.show()
        plt.close()
        if save == True:
            fig.savefig(outDir + f'/Event{event_ID[0]}.pdf')
        if counter >= n_events:
            break

def statisticalPlot(df,columns:str|list,outDir='./images',save=False):
    variables_axis_titles={'PulseHeight':'Pulse height (mV)','Charge': 'Pulse area (ADCC)','Charge_keV': 'Energy (keV)','PulseWidth': 'Pulse width (keV)','Channel_number': 'Channel','deltaT_us': r'$\Delta t$ ($\mu$ s)','Timedelta_samples': r'$\Delta t$ (samples)','Trigger_IDs': 'Trigger ID','StartPulse': 'Pulse start (sample)','EndPulse': 'Pulse end (sample)'}
    
    if isinstance(columns,str):
        columns=[columns]
    if len(columns) == 1:
        plt.hist(df[columns],bins=100)
        plt.xlabel(variables_axis_titles[columns[0]])
        plt.ylabel('Counts')
        namefig=f'hist{columns[0]}'
        plt.show()
    elif len(columns) == 2:
        if len(df.index) < 10000:
            plt.plot(df[columns[0]],df[columns[1]],'o',alpha=0.7,markersize=5)
        else:
            idx=np.random.randint(low=df.index[0],high=df.index[-1],size = 10000)
            plt.plot(df[columns[0]].iloc[idx],df[columns[1]].iloc[idx],'o',alpha=0.7,markersize=5)
        plt.xlabel(variables_axis_titles[columns[0]])
        plt.ylabel(variables_axis_titles[columns[1]])
        namefig = f'scatter{columns[0]}{columns[1]}'
        plt.show()
    else:
        raise NotImplementedError('For now only up to two variables have been implemented')
    
    if(save == True):
        p = Path(outDir)
        p.mkdir(parents=True, exist_ok=True)
        plt.tight_layout()
        plt.savefig(f'{outDir}/{namefig}.pdf')
    plt.close()

def plotFullDiagnostics(df,outDir='./images',save=False,timeWindow=12500,n_events=50):
    if ('Charge' in df.columns) & ('PulseHeight' in df.columns) & ('deltaT_us' in df.columns):
        statisticalPlot(df,'Charge_keV',outDir=outDir,save=save)
        statisticalPlot(df,'PulseHeight',outDir=outDir,save=save)
        statisticalPlot(df,['PulseHeight','Charge'],outDir=outDir,save=save)
        statisticalPlot(df,'deltaT_us',outDir=outDir,save=save)
    else:
        print('Warning: preprocess the data to get the full diagnostics!')
    statisticalPlot(df,'Channel_number',outDir=outDir,save=save)
    plot_events_coincidence(df,timeWindow=timeWindow,n_events=n_events,save=save,outDir=f'{outDir}/waveforms')
    fig=plot_rows(df)
    if save==True:
        fig.savefig(f'{outDir}/plotWfmTrigger.pdf')