"""Neutron-candidate vs accidental analysis on reduced, processed data.
 
Usage:
    python analysisWithReducedFile.py                     # default folder
    python analysisWithReducedFile.py --folder neutronBackground_GATOR --show
"""
from __future__ import annotations
 
import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from time import time
 
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
import numpy as np
import pandas as pd
 
from data_parser.Parameters import birksFunction
 
# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #
STORAGE_DIR = Path('/nfs/almond/ALMOND/')
IMAGE_ROOT = Path('/users/p/pompafra/ALMOND/neutronBackground/images')  # PERSONALIZE: where the plots are stored
DEFAULT_FOLDER = 'neutronBackground_HallC'
 
REDUCED_SUBDIR = 'reducedProcessedFiles'
DATA_FILE = 'reducedProcessed3MeVThreshold.pickle'
 
ENERGY_COLUMN = 'ScaledEnergy_keVee'
CONVERSION_TO_NCM2S = 9.16
ERR_CONVERSION_TO_NCM2S = 0.46
# The conversion to a flux was only derived for these selection thresholds
FLUX_VALID_TRIGGER_THRESHOLD = 4000   # keV
FLUX_VALID_PULSE_THRESHOLD = 50       # keVee
 
# Event selection
TRIGGER_REGION = (-1,1)              # us
TRIGGER_WINDOW = (-0.1, 0.1)          # us, pulses used to compute the trigger energy
MAX_PULSE_TIME_US = 100
SAMPLE_US = 0.016                     # us per digitizer sample
MIN_CLUSTER_GAP_SAMPLES = 5          # pulses further apart than this form separate clusters
DISTANCE_ACCIDENTALS = MIN_CLUSTER_GAP_SAMPLES * SAMPLE_US      # us, max spread of pulses within a region
SUM_ENERGY_THRESHOLD = 4000           # keV, trigger energy
SIGNAL_THRESHOLD = 50                 # keV, per-pulse and per-region threshold
 
# Inspection of single events (cluster mode)
INSPECT_N_RANDOM = 5                 # events picked at random
INSPECT_N_HIGH = 5                   # events with the highest number of clusters (signal + background)
 
# Time profile of the clusters
TIME_N_BINS = 33                      # between the trigger region and MAX_PULSE_TIME_US (3 us each)
 
# Energy spectrum
ENERGY_BIN_WIDTH = 200                # keV
ENERGY_MAX = 6000                     # keV
HIGH_ENERGY_THRESHOLD = birksFunction(3000.)         # keV, events above this are exported to csv
 
@dataclass(frozen=True)
class SiteConfig:
    """Everything that differs from one data folder to another."""
    image_subdir: str
    title: str
    excluded_period: tuple[str, str] | None = None  # inclusive, plotted and cut from rates
    data_start: str | None = None                   # keep only events after this date
 
 
SITES: dict[str, SiteConfig] = {
    'neutronBackground_HallC': SiteConfig(
        'HallC/neutronBackground', 'Hall C',
        excluded_period=('2025-05-01', '2025-08-24'), data_start='2025-08-24'),
    'neutronBackground_HallB': SiteConfig('HallB/neutronBackground', 'Hall B'),
    'neutronBackground_GATOR': SiteConfig(
        'GATOR/neutronBackground', 'Hall A',
        excluded_period=('2025-05-27', '2025-06-13')),
    'sensitivity_GATOR': SiteConfig('GATOR/sensitivity', 'Hall A'),
}
 
 
@dataclass(frozen=True)
class RateSummary:
    signal: float
    signal_err: float
    background: float
    background_err: float
 
    @property
    def net(self) -> float:
        return self.signal - self.background
 
    @property
    def net_err(self) -> float:
        return float(np.hypot(self.signal_err, self.background_err))
 
 
# --------------------------------------------------------------------------- #
# Input / setup helpers
# --------------------------------------------------------------------------- #
def get_site(folder: str) -> SiteConfig:
    if folder not in SITES:
        sys.exit(f'Folder {folder} not recognized. Known folders: {", ".join(SITES)}')
    return SITES[folder]
 
 
def make_image_dir(site: SiteConfig) -> Path:
    if not IMAGE_ROOT.exists():
        sys.exit(f'The directory {IMAGE_ROOT} does not exist.\n'
                 'Create it or change IMAGE_ROOT to the correct one.')
    image_dir = IMAGE_ROOT / site.image_subdir
    image_dir.mkdir(parents=True, exist_ok=True)
    return image_dir
 
 
def parse_excluded_period(site: SiteConfig):
    """Return (start, end) as datetime.date objects, or None."""
    if site.excluded_period is None:
        return None
    return tuple(pd.to_datetime(d).date() for d in site.excluded_period)
 
 
def read_measurement_days(folder: str) -> float:
    path = STORAGE_DIR / folder / REDUCED_SUBDIR / f'timeInformation_{folder}.csv'
    try:
        return pd.read_csv(path).EffectiveTime.values[0] / 86400.
    except Exception as exc:
        sys.exit(f'Could not read the measurement duration from {path}: {exc}')
 
 
def in_period(dates: pd.Series, period) -> pd.Series:
    """Boolean mask of dates (datetime.date objects) inside an inclusive period."""
    if period is None:
        return pd.Series(False, index=dates.index)
    return dates.between(*period)
 
 
def in_signal_window(t: pd.Series) -> pd.Series:
    """Pulse times of the signal region: -MAX_PULSE_TIME_US <= t <= TRIGGER_REGION[0]."""
    return t.between(-MAX_PULSE_TIME_US, TRIGGER_REGION[0])
 
 
def in_background_window(t: pd.Series) -> pd.Series:
    """Pulse times of the background region: TRIGGER_REGION[1] < t <= MAX_PULSE_TIME_US."""
    return (t > TRIGGER_REGION[1]) & (t <= MAX_PULSE_TIME_US)
 
 
def windowed(clusters: pd.DataFrame, region: str) -> pd.DataFrame:
    """Keep only the clusters whose time lies inside the 'signal' or 'background' window."""
    t = clusters.PulseTime_us
    return clusters[in_signal_window(t) if region == 'signal' else in_background_window(t)]
 
 
def drop_excluded(clusters: pd.DataFrame, excluded) -> pd.DataFrame:
    return clusters.loc[~in_period(clusters['Date'].dt.date, excluded)]
 
 
# --------------------------------------------------------------------------- #
# Event selection
# --------------------------------------------------------------------------- #
def load_events(path: Path, site: SiteConfig) -> pd.DataFrame:
    df = pd.read_pickle(path)
    df = df.sort_values(['Event_ID', 'PulseTime_us']).reset_index(drop=True)
    print(f'Events with coincidences (1 us): {df[np.abs(df.PulseTime_us) > 1].Event_ID.nunique()}')
    print(f'Events with coincidences (0.2,1): {df[df.PulseTime_us.between(0.2,1)].Event_ID.nunique()}')
    print(f'Events with coincidences (-1,-0.2): {df[df.PulseTime_us.between(-1,-0.2)].Event_ID.nunique()}')

    plt.hist(df[df.AveragePulsePass].PulseTime_us,bins=np.arange(-100,100,3),histtype='step',color='black')
    plt.yscale('log')
    plt.savefig(f'./PulseTimeDistribution.pdf')
    plt.close()
    # print(df[df.PulseTime_us.between(0.1,1)].set_index('Event_ID')[[ENERGY_COLUMN, 'PulseTime_us']].to_string())    
    print(f'Events in the dataframe: {df.Event_ID.nunique()}')
 
    df['Date'] = pd.to_datetime(df.Timestamp_s, unit='s')
    if site.data_start is not None:
        df = df[df.Date > site.data_start]
 
    df = df[df.AveragePulsePass & (df[ENERGY_COLUMN] > SIGNAL_THRESHOLD)].copy()
    df['PulseTime_us'] = df.PulseTime_us.round(3)
    df = df[df.PulseTime_us.between(-MAX_PULSE_TIME_US, MAX_PULSE_TIME_US)].copy()
    # Quenched energy of each pulse; energies of events/clusters are sums of these
    df['BirksEnergy'] = [birksFunction(e) for e in df[ENERGY_COLUMN]]
    return df.reset_index(drop=True)
 
 
def _event_sum(df: pd.DataFrame, mask: pd.Series) -> pd.Series:
    """Per-row sum of ENERGY_COLUMN over the pulses selected by `mask`, within each event."""
    per_event = df.loc[mask].groupby('Event_ID')[ENERGY_COLUMN].sum()
    return df['Event_ID'].map(per_event).fillna(0)
 
 
def _event_is_coincident(df: pd.DataFrame, mask: pd.Series) -> pd.Series:
    """Per-row flag: pulses of the event inside `mask` lie within DISTANCE_ACCIDENTALS.
 
    Events with no pulses in the region pass.
    """
    times = df.loc[mask].groupby('Event_ID')['PulseTime_us']
    passes = (times.max() - times.min()) < DISTANCE_ACCIDENTALS
    return df['Event_ID'].map(passes).fillna(True).astype(bool)
 
 
def select_events(df: pd.DataFrame):
    """Return the Event_IDs with a neutron candidate and with an accidental."""
    t = df.PulseTime_us
    in_trigger = t.between(*TRIGGER_WINDOW)
    in_signal = in_signal_window(t)
    in_accidental = in_background_window(t)
 
    # TODO: probably replace the trigger sum with the already present TriggerEnergy
    trigger_ok = _event_sum(df, in_trigger) > SUM_ENERGY_THRESHOLD
    signal_ok = _event_sum(df, in_signal) > SIGNAL_THRESHOLD
    accidental_ok = _event_sum(df, in_accidental) > SIGNAL_THRESHOLD
 
    candidates = df[trigger_ok & signal_ok & in_signal
                    & _event_is_coincident(df, in_signal)].Event_ID.unique()
    accidentals = df[trigger_ok & accidental_ok & in_accidental
                     & _event_is_coincident(df, in_accidental)].Event_ID.unique()
    return candidates, accidentals
 
 
def daily_counts(df: pd.DataFrame, event_ids, all_dates: pd.Index) -> pd.DataFrame:
    """Number of distinct events per calendar day (columns: Date, Event_ID)."""
    return (df[df.Event_ID.isin(event_ids)]
            .groupby(df['Date'].dt.date)['Event_ID']
            .nunique()
            .reindex(all_dates, fill_value=0)
            .reset_index())
 
 
# --------------------------------------------------------------------------- #
# Rates
# --------------------------------------------------------------------------- #
def summarize_rates(signal_daily, background_daily, total_time, excluded,
                    column='Event_ID') -> RateSummary:
    n_signal = signal_daily.loc[~in_period(signal_daily['Date'], excluded), column].sum()
    n_background = background_daily.loc[~in_period(background_daily['Date'], excluded), column].sum()
    signal = n_signal / total_time
    background = n_background / total_time
    return RateSummary(signal=signal,
                       signal_err=np.sqrt(signal / total_time),
                       background=background,
                       background_err=np.sqrt(background / total_time))
 
 
def flux_conversion_is_valid() -> bool:
    return (SUM_ENERGY_THRESHOLD == FLUX_VALID_TRIGGER_THRESHOLD
            and SIGNAL_THRESHOLD == FLUX_VALID_PULSE_THRESHOLD)
 
 
def flux_from_rate(r: RateSummary):
    """Net flux with (stat, sys) errors in 1e-7 cm^-2 s^-1, or None if the thresholds
    in use are not the ones the conversion factor is valid for."""
    if not flux_conversion_is_valid():
        return None
    scale = CONVERSION_TO_NCM2S / 10      # rate per day -> 1e-7 n cm^-2 s^-1
    sys_scale = ERR_CONVERSION_TO_NCM2S / 10
    return r.net * scale, r.net_err * scale, r.net * sys_scale
 
 
def print_rates(r: RateSummary, unit: str = 'events') -> None:
    print(f'Mean signal rate: {r.signal:.2f} +/- {r.signal_err:.2f} {unit}/day')
    print(f'Mean background rate: {r.background:.2f} +/- {r.background_err:.2f} {unit}/day')
    print(f'Net neutron rate: {r.net:.2f} +/- {r.net_err:.2f} {unit}/day')
 
    flux = flux_from_rate(r)
    if flux is None:
        print(f'Flux not computed: the conversion is only valid for a '
              f'{FLUX_VALID_TRIGGER_THRESHOLD} keV trigger threshold and a '
              f'{FLUX_VALID_PULSE_THRESHOLD} keVee pulse threshold')
        return
    value, stat, syst = flux
    print(f'Neutron flux: {value:.2f} +/- {stat:.2f} (stat) +/- {syst:.2f} (sys) x 10^-7 cm^-2 s^-1')
    print(f'Total error neutron flux (linear sum): {stat + syst:.2f} x 10^-7 cm^-2 s^-1')
    print(f'Total error neutron flux (quadrature): {np.hypot(stat, syst):.2f} x 10^-7 cm^-2 s^-1')
 
 
# --------------------------------------------------------------------------- #
# Plots
# --------------------------------------------------------------------------- #
def plot_rates(signal_daily, background_daily, rates: RateSummary, *, site, folder,
               image_dir, excluded, show=False, column='Event_ID', unit='events', tag=''):
    fig, ax = plt.subplots(figsize=(10, 5))
 
    ax.plot(signal_daily['Date'], signal_daily[column], '.', color='blue',
            label='Signal region')
    ax.axhline(rates.signal, color='blue', linestyle='--',
               label=rf'Average signal: ({rates.signal:.2f} $\pm$ {rates.signal_err:.2f}) {unit}/day')
    ax.plot(background_daily['Date'], background_daily[column], '.', color='orange',
            label='Background region')
    ax.axhline(rates.background, color='orange', linestyle='--',
               label=rf'Average background: ({rates.background:.2f} $\pm$ {rates.background_err:.2f}) {unit}/day')
 
    if excluded is not None and in_period(signal_daily['Date'], excluded).any():
        first, last = signal_daily['Date'].min(), signal_daily['Date'].max()
        start, end = max(excluded[0], first), min(excluded[1], last)
        ax.axvspan(pd.Timestamp(start), pd.Timestamp(end), color='yellow', alpha=0.5,
                   label='Excluded period')
 
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    fig.autofmt_xdate()
    ax.set_title(site.title)
    ax.set_xlabel('Date')
    ax.set_ylabel(f'{unit.capitalize()} per calendar day')
    ax.set_ylim(-0.3)
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.27), ncol=2)
    fig.tight_layout()
 
    fig.savefig(image_dir / f'hNeutronCandidatesVsAccidental_{MAX_PULSE_TIME_US:.0f}us_'
                            f'{SIGNAL_THRESHOLD:.0f}keV_{folder.split("_")[-1]}{tag}.pdf')
    if show:
        plt.show()
    plt.close(fig)
 
 
def summed_birks_energy(df, event_ids, region_mask) -> pd.Series:
    """Total quenched (Birks) energy per event, over the pulses selected by `region_mask`."""
    sel = df[df.Event_ID.isin(event_ids) & region_mask]
    return sel.groupby('Event_ID')['BirksEnergy'].sum()
 
 
def _step_errorbar(ax, x, y, width, **kwargs):
    ax.errorbar(x, y, np.sqrt(y), width / 2, fmt='.', drawstyle='steps-mid', **kwargs)
 
 
def plot_energy_histograms(signal_energies, background_energies, *, tag, image_dir):
    """Signal/background energy histograms, their csv, and the subtracted histogram."""
    signal_energies = np.asarray(signal_energies, dtype=float)
    background_energies = np.asarray(background_energies, dtype=float)
    for name, values in (('signal', signal_energies), ('background', background_energies)):
        n_nans = np.isnan(values).sum()
        if n_nans:
            print(f'Warning: {n_nans} nans present in {name} energies')
    signal_energies = signal_energies[~np.isnan(signal_energies)]
    background_energies = background_energies[~np.isnan(background_energies)]
 
    bins = np.arange(0, ENERGY_MAX + ENERGY_BIN_WIDTH, ENERGY_BIN_WIDTH)
    widths = np.diff(bins)
    ys, edges = np.histogram(signal_energies, bins=bins)
    yb, _ = np.histogram(background_energies, bins=bins)
    centers = 0.5 * (edges[1:] + edges[:-1])
 
    xlabel = 'Total energy release in proton recoils (keV)'
    ylabel = f'Counts per {ENERGY_BIN_WIDTH:.0f} keV'
 
    # Signal and background
    fig, ax = plt.subplots()
    _step_errorbar(ax, centers, ys, widths, label='Signal region', color='blue')
    _step_errorbar(ax, centers, yb, widths, label='Background region', color='orange')
    ax.set(xlabel=xlabel, ylabel=ylabel, xlim=(bins[0], bins[-1]))
    ax.legend()
    fig.tight_layout()
    fig.savefig(image_dir / f'hEnergyOfNeutronCandidates_{tag}.pdf')
    plt.close(fig)
 
    pd.DataFrame({'bin_centers': centers, 'Signal': ys, 'Background': yb}).to_csv(
        image_dir / f'hSignalBackgroundEnergies_{tag}.csv', index=False)
 
    # Background subtracted
    fig, ax = plt.subplots()
    ax.errorbar(centers, ys - yb, np.sqrt(ys + yb), widths / 2, fmt='.',
                drawstyle='steps-mid', color='blue')
    ax.set(xlabel=xlabel, ylabel=ylabel, xlim=(bins[0], bins[-1]))
    fig.tight_layout()
    fig.savefig(image_dir / f'hNeutronEnergyWithBackgroundSubtraction_{tag}.pdf')
    plt.close(fig)
 
 
def export_high_energy(table: pd.DataFrame, *, path: Path) -> None:
    """Save the entries above the histogram range, for later inspection."""
    if len(table) > 0:
        path.parent.mkdir(exist_ok=True)
        table.to_csv(path, index=False)
 
 
def plot_energy_spectra(df, candidates, accidentals, *, folder, image_dir, excluded):
    """Event-based spectra: one entry per event, summing the quenched energy of all the
    pulses of the event in the region (events failing the coincidence cut are removed)."""
    suffix = folder.split('_')[-1]
    tag = f'{MAX_PULSE_TIME_US:.0f}us_{ENERGY_COLUMN}_{suffix}_std'
 
    df = df[~in_period(df['Date'].dt.date, excluded)]
    signal_energies = summed_birks_energy(df, candidates, in_signal_window(df.PulseTime_us))
    accidental_energies = summed_birks_energy(df, accidentals, in_background_window(df.PulseTime_us))
 
    high = np.sort(np.concatenate([
        signal_energies[signal_energies > HIGH_ENERGY_THRESHOLD].index,
        accidental_energies[accidental_energies > HIGH_ENERGY_THRESHOLD].index]))
    export_high_energy(pd.DataFrame({'events': high}),
                       path=image_dir / 'highEnergyEvents' / f'eventsList_{suffix}.csv')
 
    plot_energy_histograms(signal_energies, accidental_energies, tag=tag, image_dir=image_dir)
 
 
# --------------------------------------------------------------------------- #
# Cluster-based counting
# --------------------------------------------------------------------------- #
# Alternative to the event-based counting: every group of pulses in a region is a
# "cluster", and each cluster is counted separately. Within an event, a pulse starts
# a new cluster if it is more than MIN_CLUSTER_GAP_SAMPLES samples after the
# previous pulse (the gap is measured pulse to pulse, so chains of close pulses
# stay in one cluster).
def trigger_event_ids(df: pd.DataFrame) -> pd.Index:
    """Event_IDs whose trigger energy is above SUM_ENERGY_THRESHOLD."""
    in_trigger = df.PulseTime_us.between(*TRIGGER_WINDOW)
    trigger_energy = df.loc[in_trigger].groupby('Event_ID')[ENERGY_COLUMN].sum()
    return trigger_energy.index[trigger_energy > SUM_ENERGY_THRESHOLD]
 
 
def _label_pulses(df: pd.DataFrame, event_ids, region_mask: pd.Series) -> pd.DataFrame:
    """Pulses of `event_ids` selected by `region_mask`, sorted in time, with:
    GapPrev_samples (distance to the previous pulse of the event in the region, NaN for the
    first one), ClusterNumber (1, 2, ... within event and region) and ClusterID (unique in
    the table). Used both to build the clusters and to label pulses when inspecting events.
    """
    sel = df[df.Event_ID.isin(event_ids) & region_mask].sort_values(['Event_ID', 'PulseTime_us'])
    gap_samples = (sel.groupby('Event_ID')['PulseTime_us'].diff() / SAMPLE_US).round()
    starts_cluster = gap_samples.isna() | (gap_samples > MIN_CLUSTER_GAP_SAMPLES)
    return sel.assign(GapPrev_samples=gap_samples,
                      ClusterID=starts_cluster.cumsum(),
                      ClusterNumber=starts_cluster.astype(int).groupby(sel.Event_ID).cumsum())
 
 
def _cluster_label(region: str, event_id: pd.Series, number: pd.Series) -> pd.Series:
    return region + ':' + event_id.astype(str) + ':' + number.astype(str)
 
 
def find_clusters(df: pd.DataFrame, event_ids, region_mask: pd.Series, region: str) -> pd.DataFrame:
    """One row per cluster of pulses selected by `region_mask` in the given events.
 
    Columns: ClusterLabel (region:Event_ID:number), Region, Event_ID, ClusterNumber, Date,
    PulseTime_us (first pulse), LastPulseTime_us, NPulses, Energy (summed ENERGY_COLUMN,
    used for the threshold) and BirksEnergy (sum of the quenched energies of the pulses
    of this cluster only).
 
    Pulse times are rounded to 1 ns and expected on the sample grid, so the gap in
    samples is rounded to an integer before it is compared with MIN_CLUSTER_GAP_SAMPLES.
    """
    pulses = _label_pulses(df, event_ids, region_mask)
    clusters = pulses.groupby('ClusterID').agg(
        Event_ID=('Event_ID', 'first'),
        ClusterNumber=('ClusterNumber', 'first'),
        Date=('Date', 'first'),
        PulseTime_us=('PulseTime_us', 'first'),
        LastPulseTime_us=('PulseTime_us', 'last'),
        NPulses=('PulseTime_us', 'size'),
        Energy=(ENERGY_COLUMN, 'sum'),
        BirksEnergy=('BirksEnergy', 'sum'))
    clusters['Region'] = region
    clusters['ClusterLabel'] = _cluster_label(region, clusters.Event_ID, clusters.ClusterNumber)
    clusters = clusters[clusters.Energy > SIGNAL_THRESHOLD].reset_index(drop=True)
    return clusters[['ClusterLabel', 'Region', 'Event_ID', 'ClusterNumber', 'Date',
                     'PulseTime_us', 'LastPulseTime_us', 'NPulses', 'Energy', 'BirksEnergy']]
 
 
def select_clusters(df: pd.DataFrame):
    """Return (signal_clusters, background_clusters) for the triggered events."""
    ids = trigger_event_ids(df)
    t = df.PulseTime_us
    signal = windowed(find_clusters(df, ids, in_signal_window(t), 'signal'), 'signal')
    background = windowed(find_clusters(df, ids, in_background_window(t), 'background'),
                          'background')
    return signal, background
 
 
def daily_cluster_counts(clusters: pd.DataFrame, all_dates: pd.Index) -> pd.DataFrame:
    """Number of clusters per calendar day (columns: Date, Clusters)."""
    return (clusters.groupby(clusters['Date'].dt.date).size()
            .rename('Clusters')
            .reindex(all_dates, fill_value=0)
            .reset_index())
 
 
def plot_cluster_energy_spectra(signal_clusters, background_clusters, *, folder, image_dir,
                                excluded):
    """Cluster-based spectra: one entry per cluster, with the quenched energy summed over
    the pulses of that cluster only. Only clusters in -100..-1 us (signal) and
    1..100 us (background) are used."""
    suffix = folder.split('_')[-1]
    tag = f'{MAX_PULSE_TIME_US:.0f}us_{ENERGY_COLUMN}_{suffix}_clusters'
 
    signal = drop_excluded(windowed(signal_clusters, 'signal'), excluded)
    background = drop_excluded(windowed(background_clusters, 'background'), excluded)
 
    high = pd.concat([signal[signal.BirksEnergy > HIGH_ENERGY_THRESHOLD],
                      background[background.BirksEnergy > HIGH_ENERGY_THRESHOLD]])
    export_high_energy(high.sort_values(['Event_ID', 'PulseTime_us'])[
                           ['Event_ID', 'PulseTime_us', 'BirksEnergy']],
                       path=image_dir / 'highEnergyEvents' / f'clustersList_{suffix}.csv')
 
    plot_energy_histograms(signal.BirksEnergy, background.BirksEnergy, tag=tag,
                           image_dir=image_dir)
 
 
def plot_cluster_time_profile(signal_clusters, background_clusters, *, folder, image_dir,
                              excluded):
    """Time distribution of the clusters and the background-subtracted time profile.
 
    The x axis is the distance from the trigger: signal clusters are before it,
    background clusters after it.
    """
    suffix = folder.split('_')[-1]
    tag = f'{MAX_PULSE_TIME_US:.0f}us_{suffix}'
 
    signal = drop_excluded(windowed(signal_clusters, 'signal'), excluded)
    background = drop_excluded(windowed(background_clusters, 'background'), excluded)
    dt_signal = -signal.PulseTime_us.to_numpy()          # time before the trigger
    dt_background = background.PulseTime_us.to_numpy()   # time after the trigger
 
    bins = np.linspace(TRIGGER_REGION[1], MAX_PULSE_TIME_US, TIME_N_BINS + 1)
    widths = np.diff(bins)
    centers = 0.5 * (bins[1:] + bins[:-1])
    ys, _ = np.histogram(dt_signal, bins=bins)
    yb, _ = np.histogram(dt_background, bins=bins)
 
    fig, (ax_top, ax_bottom) = plt.subplots(2, 1, figsize=(8, 7), sharex=True)
    _step_errorbar(ax_top, centers, ys, widths, label='Signal region (before trigger)',
                   color='blue')
    _step_errorbar(ax_top, centers, yb, widths, label='Background region (after trigger)',
                   color='orange')
    ax_top.set_ylabel(f'Clusters per {widths[0]:.1f} us')
    ax_top.legend()
 
    ax_bottom.errorbar(centers, ys - yb, np.sqrt(ys + yb), widths / 2, fmt='.',
                       drawstyle='steps-mid', color='blue')
    ax_bottom.axhline(0, color='grey', linestyle='--')
    ax_bottom.set_xlabel('Time distance from the trigger (us)')
    ax_bottom.set_ylabel(f'Background subtracted\nclusters per {widths[0]:.1f} us')
    ax_bottom.set_xlim(bins[0], bins[-1])
    fig.tight_layout()
    fig.savefig(image_dir / f'hClusterTimeProfile_{tag}.pdf')
    plt.close(fig)
 
    pd.DataFrame({'bin_centers_us': centers, 'Signal': ys, 'Background': yb}).to_csv(
        image_dir / f'hClusterTimeProfile_{tag}.csv', index=False)
 
 
# --------------------------------------------------------------------------- #
# Cluster multiplicity and inspection of single events
# --------------------------------------------------------------------------- #
# Multiplicity of an event = number of clusters in its signal region + in its
# background region.
REGION_COLORS = {'signal': 'blue', 'background': 'orange', 'trigger': 'red'}
 
 
def event_multiplicities(df, signal_clusters, background_clusters, excluded) -> pd.DataFrame:
    """Clusters per triggered event (events with no cluster included, excluded days removed).
 
    Index Event_ID; columns Date, Signal, Background, Total.
    """
    ids = trigger_event_ids(df)
    table = pd.DataFrame({'Date': df.groupby('Event_ID')['Date'].first().dt.date.reindex(ids)})
    table['Signal'] = signal_clusters.groupby('Event_ID').size().reindex(ids, fill_value=0)
    table['Background'] = background_clusters.groupby('Event_ID').size().reindex(ids, fill_value=0)
    table['Total'] = table.Signal + table.Background
    return table[~in_period(table['Date'], excluded)]
 
 
def plot_cluster_multiplicity(table: pd.DataFrame, *, folder, image_dir) -> None:
    """Histograms of the number of clusters per triggered event in the signal region, in the
    background region, and summed. Also saves the counts and the per-event table as csv."""
    tag = f'{MAX_PULSE_TIME_US:.0f}us_{folder.split("_")[-1]}'
    columns = ['Signal', 'Background', 'Total']
    n_max = int(table[columns].to_numpy().max()) if len(table) else 0
    n_max_sb = int(table[['Signal', 'Background']].to_numpy().max()) if len(table) else 0
 
    counts = pd.DataFrame({c: np.bincount(table[c], minlength=n_max + 1) for c in columns})
    counts.index.name = 'NClusters'
    counts.to_csv(image_dir / f'hClusterMultiplicity_{tag}.csv')
    table.to_csv(image_dir / f'clusterMultiplicityPerEvent_{tag}.csv')
    print(f'\nTriggered events by number of clusters ({len(table)} events):')
    print(counts.to_string())
 
    fig, (ax_sb, ax_tot) = plt.subplots(1, 2, figsize=(11, 4.5))
    for column, color in (('Signal', 'blue'), ('Background', 'orange')):
        ax_sb.hist(table[column], bins=np.arange(-0.5, n_max_sb + 1.5), histtype='step',
                   linewidth=1.8, color=color,
                   label=f'{column} region (mean {table[column].mean():.2f})')
    ax_tot.hist(table.Total, bins=np.arange(-0.5, n_max + 1.5), histtype='step',
                linewidth=1.8, color='black',
                label=f'Signal + background (mean {table.Total.mean():.2f})')
    for ax in (ax_sb, ax_tot):
        ax.set_yscale('log')
        ax.set_ylim(bottom=0.5)
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))
        ax.set_xlabel('Clusters per triggered event')
        ax.set_ylabel('Triggered events')
        ax.legend()
    fig.suptitle(f'{len(table)} triggered events')
    fig.tight_layout()
    fig.savefig(image_dir / f'hClusterMultiplicity_{tag}.pdf')
    plt.close(fig)
 
 
def select_events_to_inspect(table: pd.DataFrame, n_random: int, n_high: int, seed=None,
                             only_with_clusters: bool = True):
    """Event_IDs picked at random, and those with the highest multiplicity (ties broken
    randomly). With only_with_clusters=False the random pick also includes events that
    have no cluster at all, which are the majority."""
    rng = np.random.default_rng(seed)
    pool = table.index[table.Total > 0] if only_with_clusters else table.index
    random_ids = rng.choice(pool.to_numpy(), size=min(n_random, len(pool)), replace=False)
    order = table.assign(_tiebreak=rng.random(len(table))).sort_values(
        ['Total', '_tiebreak'], ascending=[False, True])
    return random_ids, order.index[:n_high].to_numpy()
 
 
def label_event_pulses(df: pd.DataFrame, event_ids) -> pd.DataFrame:
    """Every pulse of the events, with all the original columns plus Region ('signal',
    'background' or 'trigger' for -1 < t <= 1 us), ClusterLabel and GapPrev_samples."""
    t = df.PulseTime_us
    in_signal, in_background = in_signal_window(t), in_background_window(t)
    parts = []
    for region, mask in (('signal', in_signal), ('background', in_background)):
        p = _label_pulses(df, event_ids, mask)
        p['Region'] = region
        p['ClusterLabel'] = _cluster_label(region, p.Event_ID, p.ClusterNumber)
        parts.append(p.drop(columns=['ClusterID', 'ClusterNumber']))
    rest = df[df.Event_ID.isin(event_ids) & ~(in_signal | in_background)]
    parts.append(rest.assign(Region='trigger', ClusterLabel='-', GapPrev_samples=np.nan))
 
    pulses = pd.concat(parts).sort_values(['Event_ID', 'PulseTime_us'])
    first = ['Event_ID', 'Region', 'ClusterLabel', 'PulseTime_us', 'GapPrev_samples',
             ENERGY_COLUMN, 'BirksEnergy']
    return pulses[first + [c for c in pulses.columns if c not in first]]
 
 
def _decorate_time_axis(ax, energies: pd.Series) -> None:
    ax.axvspan(TRIGGER_REGION[0], TRIGGER_REGION[1], color='lightgrey', alpha=0.5)
    ax.set_xlim(-1.02 * MAX_PULSE_TIME_US, 1.02 * MAX_PULSE_TIME_US)
    ax.set_yscale('log')
    positive = energies[energies > 0]
    ax.set_ylim(bottom=positive.min() / 2 if len(positive) else 1)
    ax.set_xlabel('Time relative to the trigger (us)')
    ax.set_ylabel('Quenched energy (keV)')
    ax.legend(loc='upper right')
 
 
def plot_event_pulses(pulses: pd.DataFrame, title: str, path: Path) -> None:
    """Quenched energy of every pulse of one event as a function of time; the number next
    to a pulse is the number of the cluster it belongs to within its region."""
    fig, ax = plt.subplots(figsize=(10, 4.5))
    bottom = pulses.BirksEnergy[pulses.BirksEnergy > 0].min() / 2
    for region, color in REGION_COLORS.items():
        sel = pulses[pulses.Region == region]
        ax.vlines(sel.PulseTime_us, bottom, sel.BirksEnergy, color=color, alpha=0.6)
        ax.plot(sel.PulseTime_us, sel.BirksEnergy, 'o', ms=4, color=color,
                label=f'Pulses ({region}), n={len(sel)}')
        for p in sel[sel.Region != 'trigger'].itertuples():
            ax.annotate(p.ClusterLabel.split(':')[-1], (p.PulseTime_us, p.BirksEnergy),
                        textcoords='offset points', xytext=(3, 4), fontsize=7)
    ax.set_title(title + ': pulses', fontsize=10)
    _decorate_time_axis(ax, pulses.BirksEnergy)
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
 
 
def plot_event_clusters(clusters: pd.DataFrame, pulses: pd.DataFrame, title: str,
                        path: Path) -> None:
    """Quenched energy of every cluster of one event as a function of time (time of the
    first pulse; marker size grows with the number of pulses, shown next to the marker).
    The pulses of the trigger region are drawn for reference."""
    fig, ax = plt.subplots(figsize=(10, 4.5))
    bottom = min(clusters.BirksEnergy.min(), pulses.BirksEnergy.min()) / 2
    trig = pulses[pulses.Region == 'trigger']
    ax.vlines(trig.PulseTime_us, bottom, trig.BirksEnergy, color=REGION_COLORS['trigger'],
              alpha=0.6)
    ax.plot(trig.PulseTime_us, trig.BirksEnergy, 'o', ms=4, color=REGION_COLORS['trigger'],
            label=f'Pulses (trigger), n={len(trig)}')
    for region in ('signal', 'background'):
        sel = clusters[clusters.Region == region]
        ax.vlines(sel.PulseTime_us, bottom, sel.BirksEnergy, color=REGION_COLORS[region],
                  alpha=0.6)
        ax.scatter(sel.PulseTime_us, sel.BirksEnergy, s=30 + 25 * sel.NPulses,
                   color=REGION_COLORS[region], label=f'Clusters ({region}), n={len(sel)}')
        for c in sel.itertuples():
            ax.annotate(f'{c.NPulses}p', (c.PulseTime_us, c.BirksEnergy),
                        textcoords='offset points', xytext=(5, 5), fontsize=8)
    ax.set_title(title + ': clusters (label = number of pulses in the cluster)', fontsize=10)
    _decorate_time_axis(ax, pd.concat([clusters.BirksEnergy, trig.BirksEnergy]))
    fig.tight_layout()
    fig.savefig(path)
    plt.close(fig)
 
 
def inspect_clusters(df, signal_clusters, background_clusters, *, folder, image_dir, excluded,
                     n_random=INSPECT_N_RANDOM, n_high=INSPECT_N_HIGH, seed=None) -> None:
    """Multiplicity histograms, then for a random and a high-multiplicity selection of
    events: print every column of their clusters and pulses, and save one plot per event in
    <image_dir>/pulsesVsTime and <image_dir>/clustersVsTime."""
    table = event_multiplicities(df, signal_clusters, background_clusters, excluded)
    plot_cluster_multiplicity(table, folder=folder, image_dir=image_dir)
    # if table.empty or n_random + n_high == 0:
    #     return
 
    # random_ids, high_ids = select_events_to_inspect(table, n_random, n_high, seed)
    # pulses_dir, clusters_dir = image_dir / 'pulsesVsTime', image_dir / 'clustersVsTime'
    # pulses_dir.mkdir(exist_ok=True)
    # clusters_dir.mkdir(exist_ok=True)
 
    # all_pulses = label_event_pulses(df, pd.unique(np.concatenate([random_ids, high_ids])))
    # all_clusters = pd.concat([signal_clusters, background_clusters]).sort_values(
    #     ['Event_ID', 'PulseTime_us'])
 
    # for selection, ids in (('random', random_ids), ('highMultiplicity', high_ids)):
    #     print(f'\n{"=" * 100}\nSelection "{selection}": events {ids.tolist()}\n{"=" * 100}')
    #     for ev in ids:
    #         row = table.loc[ev]
    #         title = (f'Event {ev} ({row.Date}): {row.Signal} signal + {row.Background} '
    #                  f'background = {row.Total} clusters')
    #         ev_clusters = all_clusters[all_clusters.Event_ID == ev]
    #         ev_pulses = all_pulses[all_pulses.Event_ID == ev]
 
    #         print(f'\n--- {title} ---\nClusters:')
    #         print(ev_clusters.to_string(index=False) if len(ev_clusters) else '(none)')
    #         print('Pulses (all columns):')
    #         print(ev_pulses.to_string(index=False))    # to_string never truncates columns
 
    #         name = f'{selection}_event{ev}.pdf'
    #         plot_event_pulses(ev_pulses, title, pulses_dir / name)
    #         if len(ev_clusters):
    #             plot_event_clusters(ev_clusters, ev_pulses, title, clusters_dir / name)
 
 
def run_cluster_analysis(df, all_dates, total_time, *, site, folder, image_dir, excluded,
                         show=False, n_random=INSPECT_N_RANDOM, n_high=INSPECT_N_HIGH,
                         seed=None) -> RateSummary:
    print('\nCluster-based counting')
    signal_clusters, background_clusters = select_clusters(df)
    print(f'Clusters found: {len(signal_clusters)} signal, {len(background_clusters)} background')
 
    signal_daily = daily_cluster_counts(signal_clusters, all_dates)
    background_daily = daily_cluster_counts(background_clusters, all_dates)
 
    rates = summarize_rates(signal_daily, background_daily, total_time, excluded,
                            column='Clusters')
    print_rates(rates, unit='clusters')
 
    plot_rates(signal_daily, background_daily, rates, site=site, folder=folder,
               image_dir=image_dir, excluded=excluded, show=show,
               column='Clusters', unit='clusters', tag='_clusters')
    plot_cluster_time_profile(signal_clusters, background_clusters, folder=folder,
                              image_dir=image_dir, excluded=excluded)
    plot_cluster_energy_spectra(signal_clusters, background_clusters, folder=folder,
                                image_dir=image_dir, excluded=excluded)
    inspect_clusters(df, signal_clusters, background_clusters, folder=folder,
                     image_dir=image_dir, excluded=excluded, n_random=n_random,
                     n_high=n_high, seed=seed)
    return rates
 
 
# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main(folder: str = DEFAULT_FOLDER, show: bool = False, n_random: int = INSPECT_N_RANDOM,
         n_high: int = INSPECT_N_HIGH, seed: int | None = None) -> dict[str, RateSummary]:
    """Run both analyses and return {'events': RateSummary, 'clusters': RateSummary}."""
    start = time()
    site = get_site(folder)
    image_dir = make_image_dir(site)
    excluded = parse_excluded_period(site)
 
    total_time = read_measurement_days(folder)
    print(f'Analyzing folder {folder}')
    print(f'Measurement time (days): {total_time:.2f}')
 
    df = load_events(STORAGE_DIR / folder / REDUCED_SUBDIR / DATA_FILE, site)
    print(f'Terminated reading files in {time() - start:.2f} seconds.')
 
    candidates, accidentals = select_events(df)
 
    all_dates = pd.Index(df['Date'].dt.date.unique(), name='Date')
    signal_daily = daily_counts(df, candidates, all_dates)
    background_daily = daily_counts(df, accidentals, all_dates)
 
    rates = summarize_rates(signal_daily, background_daily, total_time, excluded)
    print_rates(rates)
 
    plot_rates(signal_daily, background_daily, rates, site=site, folder=folder,
               image_dir=image_dir, excluded=excluded, show=show)
    plot_energy_spectra(df, candidates, accidentals, folder=folder,
                        image_dir=image_dir, excluded=excluded)
 
    cluster_rates = run_cluster_analysis(df, all_dates, total_time, site=site, folder=folder,
                                         image_dir=image_dir, excluded=excluded, show=show,
                                         n_random=n_random, n_high=n_high, seed=seed)
 
    print(f'Elapsed time: {time() - start:.2f} seconds.')
    return {'events': rates, 'clusters': cluster_rates}
 
 
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--folder', default=DEFAULT_FOLDER, choices=list(SITES))
    parser.add_argument('--show', action='store_true', help='display the rate plot')
    parser.add_argument('--n-random', type=int, default=INSPECT_N_RANDOM,
                        help='events picked at random for the printed/plotted inspection')
    parser.add_argument('--n-high', type=int, default=INSPECT_N_HIGH,
                        help='events with the highest number of clusters to inspect')
    parser.add_argument('--seed', type=int, default=None,
                        help='seed of the random selection (default: different each run)')
    args = parser.parse_args()
    main(args.folder, args.show, args.n_random, args.n_high, args.seed)
 