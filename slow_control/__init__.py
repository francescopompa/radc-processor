from data_parser.data_io import make_total_dataFrame_processed
from glob import glob
import data_parser.plotting as pl
import time
import matplotlib.pyplot as plt
import plotly.express as px
from jinja2 import Template
import pandas as pd
import plotly.express as px
from udp_receiver.receiver_class import convert_seconds
from preprocess_data import Parameters
import numpy as np
from http.server import HTTPServer, BaseHTTPRequestHandler
# based on https://plotly.com/python/interactive-html-export/


class Control():

    _base_path = "/data/DAQMeasurements"

    def __init__(self,
                 target_root=_base_path,
                 target_dir=time.strftime("%Y-%m-%d"),
                 target_file=None,
                 output_html_path=r"/home/mnd/Desktop/online_analysis.html",
                 input_template_path=r"/home/mnd/Software/radc-processor/slow_control/template.html"
                 ) -> None:

        self.target_root = target_root
        self.target_dir = target_dir
        self.target_file = target_file
        self.n_files = len(
            glob(f'{self.target_root}/{self.target_dir}/data/*.bin'))
        self.output_html_path = output_html_path
        self.input_template_path = input_template_path

        
        self.start()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        exit()
    
    def getMetadata(self,df,file,previous_metadata = pd.DataFrame()):
        metadata = {}
        totalTime = df.Timestamp_s.iloc[-1] - df.Timestamp_s.iloc[0]
        metadata['Measurement number'] = file.split('.')[-3] if 'chunk' in file else file.split('.')[-2]
        metadata['Chunk number'] = file.split('.')[-2] if 'chunk' in file else 0
        metadata['Elapsed time'] = convert_seconds(totalTime)
        metadata['Snippet rate'] = convert_units(len(df) / totalTime,'Hz')
        metadata['Event rate'] = convert_units(len(set(df['Event_ID'])) / totalTime,'Hz')
        metadata['Pulse detection efficiency (%)'] = len(
            df[df.IsPulse == True]) / len(df) * 100
        metadata['Corrupted snippets fraction (%)'] = len(
            df[df.preprocessingFlags != ""])/len(df) * 100
        small_df = pd.DataFrame(metadata,index=[0])
        df_info = pd.concat([previous_metadata,small_df])
        return df_info


    def generate_plots(self, previous_metadata=pd.DataFrame(),file=None):
        print('Generating plots...')
        _, df = make_total_dataFrame_processed(file)
        df_info = self.getMetadata(df,file,previous_metadata)
        fig, ax = plt.subplots()
        pl.plotCountsPerChannel(df, ax)
        fig.savefig('/home/mnd/Desktop/hCountsPerChannel.png')
        plt.close()
        fig = px.histogram(x=df['deltaT_us'][df.IsPulse == True], log_y=True)
        fig.update_traces(xbins=dict(
            start=-Parameters.PostTriggerTime*16e-3,
            end=Parameters.PostTriggerTime*16e-3,
            size=0.048
        ))
        fig.update_layout(
            autosize=False,
            height=400,
            width=600,
            xaxis_title='Time (us)',
            yaxis_title='Counts',
            title='Time distribution of all pulses'
        )
        # consider also defining the include_plotlyjs parameter to point to an external Plotly.js as described above
        centerEnergy = df[(df.deltaT_us < 0.15) & (df.deltaT_us>-0.15)].groupby('Event_ID').Charge_keV.sum()
        beforeTriggerEnergy = df[df.deltaT_us<-0.15].groupby('Event_ID').Charge_keV.sum()
        afterTriggerEnergy = df[df.deltaT_us>0.15].groupby('Event_ID').Charge_keV.sum()

        fig_trigger = px.histogram(x=centerEnergy, log_y=True)
        fig_trigger.update_traces(xbins=dict(
            start=0,
            end=8000,
            size=50
        ))
        fig_trigger.update_layout(
            autosize=False,
            height=400,
            width=600,
            xaxis_title='Energy (keV)',
            yaxis_title='Counts',
            title='Summed energy in the trigger region'
        )
        
        tmp_df=pd.DataFrame(dict(
            series=np.concatenate((["before"]*len(beforeTriggerEnergy),["after"]*len(afterTriggerEnergy))),
            data=np.concatenate((beforeTriggerEnergy, afterTriggerEnergy)))
        )
        fig_comparison=px.histogram(tmp_df,x="data",color="series",barmode="overlay",log_y=True)
        fig_comparison.update_traces(xbins=dict(
            start=0,
            end=4000,
            size=20
        ))
        fig_comparison.update_layout(
            autosize=False,
            height=400,
            width=600,
            xaxis_title='Energy (keV)',
            yaxis_title='Counts',
            title='Summed energy before and after the trigger'
        )
        
        

        context = {
            "fig": fig.to_html(full_html=False),
            "table": df_info.tail(10).to_html( index=False, float_format="%.4g", justify='left'),
            "title": f"Analysis of file {file}",
            "fig_trigger":fig_trigger.to_html(full_html=False),
            "fig_comp":fig_comparison.to_html(full_html=False)

        }
        
        with open(self.output_html_path, "w", encoding="utf-8") as output_file:
            with open(self.input_template_path) as template_file:
                j2_template = Template(template_file.read())
                output_file.write(j2_template.render(context))

        print(f"You can see the plots at file://{self.output_html_path}\n\n")
        return df_info

    def start(self):
        print('Starting...')
        metadata=pd.DataFrame()
        if self.target_file is None and self.target_dir is not None:
            files = glob(f'{self.target_root}/{self.target_dir}/data/*.bin')
            files.sort()

            while True:
                files = glob(
                    f'{self.target_root}/{self.target_dir}/data/*.bin')
                files.sort()
                print(f"Analyzing {files[-1]}... ")
                metadata = self.generate_plots(file=files[-1],previous_metadata=metadata)
        
        else:
            self.generate_plots(
                f'{self.target_root}/{self.target_dir}/{self.target_file}')

    def switch_file(self, file):
        # check for not existent file
        self.target_file = file
        self.generate_plots(file)

def convert_units(size,unit:str):
    prefixes = ['','k','M','G','T']
    units = [p + unit for p in prefixes]
    for x in units:
        if size < 1000.:
            return "%3.3f %s" % (size, x)
        size /= 1000.

    return size