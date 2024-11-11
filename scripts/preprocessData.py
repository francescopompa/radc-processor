from data_parser.data_io import make_total_rootfile
import os
from glob import glob
from time import time
import json
from udp_receiver.receiver_class import convert_seconds
import sys


def main():
   if len(sys.argv) > 1:
        folder = sys.argv[1]
    else:
        folder = 'FNG'
#    baseDir = f'/kalinka/storage/darkmatter/lngs-neutron-detector/{folder}'
    baseDir = f'/mnt'
    subdirectories = [x[0] for x in os.walk(baseDir)]
    n_jobs = 20
    begin = time()

    for s in subdirectories:
        json_files = glob(f'{s}/*results*.json')
        for i,j in enumerate(json_files):
            start = time()
            with open(j, 'r') as file:
                metadata = json.load(file)
            print(f'Subdirectory: {s}')
            if ('processed' not in metadata or metadata['processed'] == False) and 'files_written' in metadata:
                namefiles = [m.split('/')[-1] for m in metadata['files_written']]
                namefile_output = namefiles[0].split('.')[0]
                namefiles = [f'{s}/{name}' for name in namefiles]
                print(f'Analyzing {len(namefiles)} files from json file {i+1}/{len(json_files)}')
                
                if "SLURM_JOB_ID" not in os.environ:
                    n_jobs=min(len(namefiles),4)
                
                processingMetadata = make_total_rootfile(
                    namefiles , out_dir=f'{s}/processed/', namefile_output=namefile_output, mode='compact', parallel=True, n_jobs=n_jobs
                    )
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
