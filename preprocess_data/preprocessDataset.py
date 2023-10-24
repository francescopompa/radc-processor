from import_helper import *
list_imports()
import matplotlib.pyplot as plt
from pathlib import Path
from peak_finding_algorithms import *
import sys
from time import process_time

start=process_time()
data_dir='.'
out_dir='.'

namefile_data=sys.argv[0]
namefile_output=sys.argv[1]
tracelength=int(sys.argv[2])

data_to_root(data_dir,namefile_data,tracelength,out_dir,namefile_output)

