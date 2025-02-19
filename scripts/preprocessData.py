from data_parser.data_io import make_total_rootfile
import os
from glob import glob
from time import time, strftime
import json
from udp_receiver.receiver_class import convert_seconds
from argparse import ArgumentParser
from data_parser import Parameters
import subprocess
from pathlib import Path

def getCommit():
    return subprocess.check_output(["git", "describe", "--always"], cwd=Path(__file__).resolve().parent).strip().decode()

def main():

    parser = ArgumentParser()
    parser.add_argument("-f", "--force",
                        action="store_true", default=False,
                        help="Forces processing of all files in the folder.")
    parser.add_argument("-m","--matchMaximum",
                        action="store_true", default=False,
                        help="It makes the pulse finding match the maximum for RMS calculation.\n" 
                        "To be used with dated datasets." )
    parser.add_argument("-n","--keepNumber",
                        action="store_true", default=False,
                        help="It keeps the number of the measurement in the name of the output file. To be used with files named sequentially.\n" 
                        "To be used with dated datasets." )
    parser.add_argument("-r", "--relative",
                        help="Sets the directory relative to /kalinka/storage/darkmatter/lngs-neutron-detector.")
    parser.add_argument("-a", "--absolute",
                        help="Sets the absolute path of the directory to be processed.")
    parser.add_argument("-o", "--output",
                        help="Sets the path of the output files.")
    parser.add_argument("-b","--BGOchannel", type=int,
                        default=Parameters.BGO_channel, choices=range(37),
                        metavar='0:36',
                        help="Sets the channel of the BGO for correct pulse analysis.")
    parser.add_argument("-g","--gain",
                        default=Parameters.gain,
                        help="Sets the gain of the PMTs for energy determination. It can be 'matched_v{Version}' or a numeric value")
    parser.add_argument("-t","--threshold", type=float,
                        default=Parameters.RE_threshold,
                        help='It sets the default threshold for the average pulse cut.')

    parser.print_help()

    args = vars(parser.parse_args())

    Parameters.BGO_channel = args['BGOchannel']
    Parameters.gain = args['gain']
    Parameters.match_pulse_maximum = args['matchMaximum']
    Parameters.RE_threshold = args['threshold']
    
    if args['absolute'] is not None and args['relative'] is not None:
        print('Impossible to set relative and absolute path of the directory at the same time.')
        exit()
    elif args['relative'] is not None:
        baseDir = f'/kalinka/storage/darkmatter/lngs-neutron-detector/{args["relative"]}'
    elif args['absolute'] is not None:
        baseDir = args['absolute']
    else:
        print('It is required to set a folder to be processed.')
        exit()

    forcePreprocessing = args['force']
    keepMeasurementNumber = args['keepNumber']

    print(f'Processing directory {baseDir}.')
    if forcePreprocessing:
        print('All files in the directory will be processed.')
    print(f'You are processing the dataset with the following parameters:\n'
          f'BGO channel: {Parameters.BGO_channel}\n'
          f'Gain: {Parameters.gain}\n'
          f'Threshold of the RMS cut: {Parameters.RE_threshold}')
    if Parameters.match_pulse_maximum:
        print('The RMS cut will try to match the pulse maxima.')
    
    if not os.path.isdir(baseDir):
        print('The directory does not exist.')
        exit()

    subdirectories = [x[0] for x in os.walk(baseDir)]
    n_jobs = -1
    begin = time()

    for s in subdirectories:
        json_files = glob(f'{s}/*results*.json')
        for i, j in enumerate(json_files):
            start = time()
            with open(j, 'r') as file:
                metadata = json.load(file)
            print(f'Subdirectory: {s}')
            if (('processed' not in metadata or metadata['processed'] == False) and 'files_written' in metadata) | forcePreprocessing:
                namefiles = [m.split('/')[-1]
                             for m in metadata['files_written']]
                namefile_output = namefiles[0].split('.')[0]
                if keepMeasurementNumber:
                    namefile_output = f"{namefiles[0].split('.')[0]}.{namefiles[0].split('.')[1]}"
                namefiles = [f'{s}/{name}' for name in namefiles]
                print(
                    f'Analyzing {len(namefiles)} files from json file {i+1}/{len(json_files)}')

                if all(os.stat(namefile).st_size == 0 for namefile in namefiles):
                    print(
                        f'Warning: All binaries for {j} were empty. Continuing with next .json')
                    continue

                if "SLURM_JOB_ID" not in os.environ:
                    n_jobs = min(len(namefiles), 4)

                outDir = s
                if args['output'] is not None:
                    outDir = args['output']
                else:
                    outDir = f'{s}/processed/'

                processingMetadata = make_total_rootfile(
                    namefiles, out_dir=outDir, namefile_output=namefile_output, mode='compact', parallel=True, n_jobs=n_jobs
                )
                processingDuration = time() - start
                processingTime = strftime('%Y/%m/%d %H:%M:%S')
                metadata['processing_duration'] = processingDuration
                metadata['processed'] = True
                metadata['processing_time'] = processingTime
                processingMetadata['processing_duration'] = processingDuration
                processingMetadata['processed'] = True
                processingMetadata['processing_time'] = processingTime
                processingMetadata['commit'] = getCommit()
                with open(j, 'w+') as file:
                    json.dump(metadata, file, indent=4)
                with open(f'{outDir}/{namefile_output}.json', 'w+') as file:
                    json.dump(processingMetadata, file, indent=4)

    print(f'Elapsed time: {convert_seconds(time()-begin)} s.')


if __name__ == '__main__':
    main()
