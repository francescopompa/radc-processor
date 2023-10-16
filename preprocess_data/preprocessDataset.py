from import_helper import *
list_imports()
import matplotlib.pyplot as plt
from pathlib import Path
from peak_finding_algorithms import *
import sys

data_dir=Path('.')
out_dir=Path('.')

namefile_data=sys.argv[0]
namefile_output=sys.argv[1]
tracelength=int(sys.argv[2])

df = struct_conversion.DataFile(
    data_dir / namefile_data,
    tracelength=tracelength
    )

pdf = data_io.make_total_dataFrame([df])
pulses=np.array(pdf.samples)
pulses=np.stack(pulses,axis=0)
successes,max_indices,pulse_heights,pulse_widths,areas,starts,ends = loop_over_events(pulses) 
pdf['IsPulse']=successes
pdf['MaxIndex']=max_indices
pdf['PulseHeights']=pulse_heights
pdf['PulseWidths']=pulse_widths
pdf['Charge']=areas
pdf['StartPulse']=starts
pdf['EndPulse']=ends
print(pdf.columns)
df_to_root_file(pdf,out_dir,namefile_output)
