from pathlib import Path
import peak_finding_algorithms as pf
import sys

data_dir = sys.argv[1]
namefile_data = sys.argv[2]
out_dir = sys.argv[3]
namefile_output = sys.argv[4]
tracelength = int(sys.argv[5])

pf.single_dataset_to_root(data_dir, namefile_data,
                          out_dir, namefile_output, tracelength=tracelength)
