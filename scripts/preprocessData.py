from data_parser.data_io import make_total_rootfile
import os
from glob import glob
from time import time
import json
from udp_receiver.receiver_class import convert_seconds
from argparse import ArgumentParser


def main():

    parser = ArgumentParser()
    parser.add_argument("-r", "--relative",
                        help="Sets the directory relative to /kalinka/storage/darkmatter/lngs-neutron-detector.")
    parser.add_argument("-a", "--absolute",
                        help="Sets the absolute path of the directory to be processed.")
    parser.add_argument("-o", "--output",
                        help="Sets the path of the output files.")
    parser.add_argument("-f", "--force",
                        action="store_true", default=False,
                        help="Forces processing of all files in the folder.")

    parser.print_help()

    args = vars(parser.parse_args())
    
    if args['absolute'] is not None and args['relative'] is not None:
        print('Impossible to set relative and absolute path of the directory at the same time.')
        exit()
    elif args['relative'] is not None:
        baseDir = f'/kalinka/storage/darkmatter/lngs-neutron-detector/{args["relative"]}'
    elif args['absolute'] is not None:
        baseDir = args['absolute']
    else:
        print('It is required to set a folder to process.')
        exit()

    forcePreprocessing = args['force']

    print(f'Processing directory {baseDir}.')
    if forcePreprocessing:
        print('All files in the directory will be processed.')

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
                namefiles = [f'{s}/{name}' for name in namefiles]
                print(
                    f'Analyzing {len(namefiles)} files from json file {i+1}/{len(json_files)}')

                if all(os.stat(namefile).st_size == 0 for namefile in namefiles):
                    print(
                        f'Warning: All binaries for {j} where empty. Continuing with next .json')
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
                processingTime = time() - start
                metadata['processing_time'] = processingTime
                metadata['processed'] = True
                processingMetadata['processing_time'] = processingTime
                processingMetadata['processed'] = True
                with open(j, 'w+') as file:
                    json.dump(metadata, file, indent=4)
                with open(f'{outDir}/{namefile_output}.json', 'w+') as file:
                    json.dump(processingMetadata, file, indent=4)

    print(f'Elapsed time: {convert_seconds(time()-begin)} s.')


if __name__ == '__main__':
    main()
