import gc
import json
import shutil
import tempfile
import traceback
from argparse import ArgumentParser
from glob import glob
from pathlib import Path
from time import time

import numpy as np
import pandas as pd

from analysisScripts import periodicGammaCalibration
from data_parser import Parameters
from data_parser.data_io import (
    build_rootfile,
    compactDataframe,
    findAccidentalCoincidencesTriggerRegion,
    reorderEventIDs,
)
from udp_receiver.receiver_class import convert_seconds

# ---------------------------------------------------------------------------
# Memory strategy
# ---------------------------------------------------------------------------
# The original script kept every pulse of the whole dataset in a single
# DataFrame (plus several copies of it).  Here the data is streamed:
#
#   pass 1: read one source pickle at a time, keep only the needed columns and
#           bucket the rows by week into small temporary pickles on disk.
#           Only the Event_IDs (1 int column) are kept in RAM, because
#           reorderEventIDs needs to see all of them at once.
#   pass 2: load ONE week at a time, apply the reordered Event_IDs and write the
#           weekly gamma-calibration inputs.  The week is stored again on disk.
#   pass 3: after periodicGammaCalibration, load ONE week at a time, apply the
#           energy correction, remove accidental coincidences, select events
#           and keep only the (reduced) rows that end up in the output.
#
# Peak RAM is therefore ~ max(one source pickle with waveforms, one week of
# reduced columns, the final reduced output) instead of the entire dataset.
# ---------------------------------------------------------------------------

storageDir = '/nfs/almond/ALMOND/'

sumChannelThreshold = 3000
withEnergyCorrection = True

# Columns read from the source pickles (everything else, e.g. PulseWaveform, is dropped immediately)
base_columns = ['Event_ID', 'Timestamp_s', 'PulseTime_us', 'PulseAreaADCC',
                'AveragePulsePass', 'Channel_number', 'ApproxEnergy_keVee']
columns_for_gammaCalibration = ['Event_ID', 'PulseAreaADCC', 'ApproxEnergy_keVee', 'PulseTime_us', 'Channel_number']

# (start condition, end condition) used to compute the time to be subtracted.
# t1 = first row (in file order) satisfying start condition, t2 = last row satisfying end condition.
TIME_WINDOWS = {
    'neutronBackground_GATOR': (lambda dt: dt > '2025-05-27', lambda dt: dt < '2025-06-13'),
    'neutronBackground_HallC': (lambda dt: dt < '2025-08-23', lambda dt: dt < '2025-08-23'),
}


def getTimeFromJsonFiles(files):
    """
    Extracts the time from JSON files.
    """
    total_time = 0
    for file in files:
        with open(file, 'r') as f:
            data = json.load(f)
            total_time += data['total_time']
    return total_time


def loadEnergyCorrection(folder):
    """
    Reads the calibration table once. Returns None if it is not available
    (the reduction then runs without energy correction, as before).
    """
    try:
        E_cor = pd.read_csv(f'{storageDir}/{folder}/gammaCalibration/gammaCalibrationResults/gammaCalibrationResults_{folder}.csv')
        E_cor = E_cor.rename(columns={'channel': 'Channel_number'})
        E_cor['date'] = pd.to_datetime(E_cor['date'])
        # only the columns that are used, so the merge does not add anything else to the data
        return E_cor[['date', 'Channel_number', 'CF', 'Fitted_CF']]
    except Exception as e:
        print('Error details')
        print(f"Type: {type(e).__name__}")
        print(f"Message: {e}")
        print(traceback.format_exc())
        print('File not found: running first without energy correction')
        return None


def correctEnergy(df, E_cor):
    baseCF = 1.
    df['date'] = df['datetime'].dt.to_period('W-SAT').dt.start_time
    df = df.merge(E_cor, on=['date', 'Channel_number'])  # inner merge, as in the original
    df['ScaledEnergy_keVee'] = df['ApproxEnergy_keVee'] * baseCF / df['CF']
    df['ScaledEnergy_keVee_2'] = df['ApproxEnergy_keVee'] * baseCF / df['Fitted_CF']
    return df.drop(columns=['CF', 'Fitted_CF'])


def writeGammaCalibrationInputs(week, date_str, outputGammaDir):
    for ch in range(36):
        df_ch = week[week.Channel_number == ch]
        if len(df_ch) > 0:
            p = Path(f'{outputGammaDir}/{date_str}')
            p.mkdir(parents=True, exist_ok=True)
            df_ch = df_ch[columns_for_gammaCalibration].reset_index(drop=True)
            df_ch.to_pickle(f'{outputGammaDir}/{date_str}/channel{ch}.pickle')
            build_rootfile(df_ch, {}, f'{outputGammaDir}/{date_str}', f'channel_{ch}', 0)


def main():
    start = time()

    folder = 'neutronBackground_HallB'
    parser = ArgumentParser()
    parser.add_argument("-d", "--directory",
                        help=f"Sets the directory relative to {Parameters.storage_directory}/ALMOND/ where the data is stored. Default: {folder}",
                        default=folder)
    parser.print_help()
    args = vars(parser.parse_args())
    if args['directory'] is not None:
        folder = args['directory']

    baseDir = f'{storageDir}/'
    outputDir = f'{baseDir}/{folder}/reducedProcessedFiles/'
    outputGammaDir = f'{baseDir}/{folder}/gammaCalibration/'
    Path(outputDir).mkdir(parents=True, exist_ok=True)

    print(f'Reading files from {baseDir}/{folder}...')

    files = glob(f'{baseDir}/{folder}/processed/*.pickle')
    if folder == 'testDataset':
        files = glob(f'{baseDir}/{folder}/*.pickle')
    files.sort()

    # Temporary storage lives next to the outputs (big disk), and is removed automatically
    with tempfile.TemporaryDirectory(dir=outputDir, prefix='tmp_reduce_') as tmpdir:
        tmpdir = Path(tmpdir)
        chunks_dir = tmpdir / 'chunks'
        weeks_dir = tmpdir / 'weeks'
        weeks_dir.mkdir()

        # ------------------------------------------------------------------
        # PASS 1: stream the source files, bucket rows by week on disk
        # ------------------------------------------------------------------
        metadata = {}
        id_parts = []
        row_offset = 0
        t_first = None
        t_last = None
        window = TIME_WINDOWS.get(folder)

        for i, f in enumerate(files):
            tmp = pd.read_pickle(f)
            metadata = tmp.attrs
            chunk = tmp[base_columns]          # copy of the needed columns only
            del tmp                            # frees PulseWaveform & co.
            gc.collect()

            id_parts.append(chunk['Event_ID'].to_numpy())
            chunk = chunk.assign(
                _row=np.arange(row_offset, row_offset + len(chunk), dtype=np.int64),
                datetime=pd.to_datetime(chunk.Timestamp_s, unit='s'),
            )
            row_offset += len(chunk)

            if window is not None:
                dt_values = chunk['datetime'].to_numpy()
                if t_first is None:
                    m = window[0](chunk['datetime']).to_numpy()
                    if m.any():
                        t_first = dt_values[m][0]
                m = window[1](chunk['datetime']).to_numpy()
                if m.any():
                    t_last = dt_values[m][-1]

            for d, g in chunk.groupby(pd.Grouper(key='datetime', freq='W', label='left')):
                if len(g) == 0:
                    continue
                wdir = chunks_dir / d.strftime('%Y-%m-%d')
                wdir.mkdir(parents=True, exist_ok=True)
                g.to_pickle(wdir / f'{i:06d}.pickle')

            del chunk
            gc.collect()

        print(f'Terminated reading {len(files)} files after {convert_seconds(time() - start)}.')

        # Event_ID reordering needs the complete Event_ID column, but only that column
        all_ids = np.concatenate(id_parts)
        del id_parts
        new_ids = np.asarray(reorderEventIDs(pd.Series(all_ids)))
        del all_ids

        total_time = getTimeFromJsonFiles(glob(f'{baseDir}/{folder}/processed/*.json'))

        # Time to be subtracted
        time_to_subtract_s = 0
        if window is not None:
            if t_first is None or t_last is None:
                raise ValueError(f'Could not find the rows delimiting the time window for {folder}')
            time_to_subtract_s = (t_last - t_first) / np.timedelta64(1, 's')

        print(f'Calculated time from the json: {total_time / 86400:.3f} days')
        print(f'Time to be subtracted: {time_to_subtract_s / 86400:.3f} days')
        print(f'Total time (real): {(total_time - time_to_subtract_s) / 86400:.3f} days.')

        days = pd.DataFrame({'TotalTime': total_time,
                             'TimeToSubtract': time_to_subtract_s,
                             'EffectiveTime': total_time - time_to_subtract_s,
                             'EffectiveTime_days': (total_time - time_to_subtract_s) / 86400.}, index=[0])
        days.to_csv(f'{outputDir}/timeInformation_{folder}.csv', index=False, float_format='%.3f')

        # ------------------------------------------------------------------
        # PASS 2: one week at a time -> gamma-calibration inputs
        # ------------------------------------------------------------------
        for wdir in sorted(chunks_dir.iterdir()):
            date_str = wdir.name
            print(f'Processing week starting at {date_str}...')
            week = pd.concat([pd.read_pickle(p) for p in sorted(wdir.glob('*.pickle'))], ignore_index=True)
            week.loc[:, 'Event_ID'] = new_ids[week['_row'].to_numpy()]

            writeGammaCalibrationInputs(week, date_str, outputGammaDir)

            week.to_pickle(weeks_dir / f'{date_str}.pickle')
            del week
            shutil.rmtree(wdir)
            gc.collect()
        del new_ids
        gc.collect()

        periodicGammaCalibration(folder=folder)

        E_cor = loadEnergyCorrection(folder) if withEnergyCorrection else None

        columns_to_save = list(base_columns)
        if E_cor is not None:
            columns_to_save += ['ScaledEnergy_keVee', 'ScaledEnergy_keVee_2']
        energy_column = 'ScaledEnergy_keVee' if E_cor is not None else 'ApproxEnergy_keVee'

        # ------------------------------------------------------------------
        # PASS 3: one week at a time -> energy correction, cleaning, selection
        # ------------------------------------------------------------------
        parts = []
        total_ids, ids_3MeV, ids_coinc = [], [], []

        for wpath in sorted(weeks_dir.glob('*.pickle')):
            week = pd.read_pickle(wpath)
            if E_cor is not None:
                week = correctEnergy(week, E_cor)
            week.attrs = metadata
            if week.empty:
                continue

            # not sure if really needed
            findAccidentalCoincidencesTriggerRegion(week)
            week = week[week.AccidentalCoincidenceFlag == False].reset_index(drop=True)
            if week.empty:
                continue

            sumenergy = week[np.abs(week.PulseTime_us) < 0.1].groupby('Event_ID')[energy_column].agg('sum')
            events3MeV = np.array(sumenergy[sumenergy > sumChannelThreshold].index)
            eventsWithCoincidences = week[np.abs(week.PulseTime_us) > 0.2].Event_ID.unique()
            events_both = np.intersect1d(events3MeV, eventsWithCoincidences)

            total_ids.append(week.Event_ID.unique())
            ids_3MeV.append(events3MeV)
            ids_coinc.append(eventsWithCoincidences)

            keep = week.Event_ID.isin(eventsWithCoincidences).to_numpy()
            if keep.any():
                sub = week.loc[keep, columns_to_save + ['_row']].assign(
                    _in3MeV=week.Event_ID[keep].isin(events_both).to_numpy())
                parts.append(sub)

            del week
            gc.collect()

    # temporary directory is gone from here on
    n_total = len(np.unique(np.concatenate(total_ids)))
    n_3MeV = len(np.unique(np.concatenate(ids_3MeV)))
    n_coinc = len(np.unique(np.concatenate(ids_coinc)))
    n_both = len(np.intersect1d(np.concatenate(ids_3MeV), np.concatenate(ids_coinc)))
    del total_ids, ids_3MeV, ids_coinc

    # Take only events with coincidences and events with energy above threshold
    print(f'Event above 3 MeV over total: {n_3MeV / n_total:.2%}')
    print(f'Events with coincidences over total: {n_coinc / n_total:.2%}')
    print(f'Events with coincidences above 3 MeV: {n_both / n_total:.2%}')

    # creation of reduced dataframes happens here
    if parts:
        df_r = pd.concat(parts, ignore_index=True)
    else:
        df_r = pd.DataFrame(columns=columns_to_save + ['_row', '_in3MeV'])
    del parts
    gc.collect()

    # restore the original row order (rows were processed week by week)
    if not df_r['_row'].is_monotonic_increasing:
        df_r = df_r.sort_values('_row', kind='stable', ignore_index=True)
    df_r.pop('_row')
    mask_3MeV = df_r.pop('_in3MeV').to_numpy(dtype=bool)

    df_r2 = df_r[mask_3MeV].reset_index(drop=True)

    print(f'Events in the first reduced dataframe: {df_r.Event_ID.nunique()}')
    print(f'Events in the second reduced dataframe (3 MeV threshold): {df_r2.Event_ID.nunique()}')

    df_r.to_pickle(f'{outputDir}/reducedProcessed.pickle')
    df_r2.to_pickle(f'{outputDir}/reducedProcessed3MeVThreshold.pickle')

    # root
    df_r = compactDataframe(df_r)
    build_rootfile(df_r, {}, outputDir, 'processedData', 0)
    del df_r
    gc.collect()
    df_r2 = compactDataframe(df_r2)
    build_rootfile(df_r2, {}, outputDir, 'processedData3MeVThreshold', 0)

    print(f'Completed creation of reduced root files after {convert_seconds(time() - start)}.')
    print(f'Time elapsed: {convert_seconds(time() - start)}.')


if __name__ == '__main__':
    main()
