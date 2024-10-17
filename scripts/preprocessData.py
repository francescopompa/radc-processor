from data_parser.data_io import make_total_rootfile
import os
from glob import glob
from time import time
import json
from udp_receiver.receiver_class import convert_seconds
import sys

# first follow the instructions on this question: https://unix.stackexchange.com/questions/454957/cron-job-to-run-under-conda-virtual-environment
# the use the command crontab -e to write:
# SHELL=/bin/bash
# BASH_ENV=~/.bashrc_conda
# 0 3 * * * /bin/bash preprocessData.sh > /dev/null 2>&1
# there are still some possibilities of improvemement here, like:
# 1. informative output to json file

def main():
    if len(sys.argv) > 1:
        folder = sys.argv[1]
    else:
        folder = 'neutronDetectorData'
    baseDir = '/kalinka/storage/darkmatter/lngs-neutron-detector/' + folder
    subdirectories = [x[0] for x in os.walk(baseDir) if x[0] != baseDir]
    namefile = 'processed.json'
    begin = time()


    # change by using the files field in the json files
    for s in subdirectories:
        start = time()
        json_files = glob(f'{s}/*results*.json')
        for j in json_files:
            with open(j, 'r') as file:
                metadata = json.load(file)
            print(f'Subdirectory: {s}')
            if ('processed' not in metadata or metadata['processed'] == False) and 'files_written' in metadata:
                namefiles = [m.split('/')[-1] for m in metadata['files_written']]
                namefile_output = namefiles[0].split('.')[0]
                namefiles = [f'{s}/{name}' for name in namefiles]
                print(f'Analyzing files: {namefiles}')
                processingMetadata = make_total_rootfile(
                    namefiles , out_dir=f'{s}/processed/', namefile_output=namefile_output, mode='compact', parallel=True, n_jobs=min(len(metadata['files_written']), 4))
                metadata['processing_time'] = time() - start
                metadata['processed'] = True
                processingMetadata['processing_time'] = time() - start
                processingMetadata['processed'] = True
                with open(j, 'w+') as file:
                    json.dump(metadata, file, indent=4)
                with open(f'{s}/processed/{namefile_output}.json', 'w+') as file:
                    json.dump(processingMetadata, file, indent=4)


    print(f'Elapsed time: {convert_seconds(time()-begin)} s.')

if __name__ == '__main__':
    main()
