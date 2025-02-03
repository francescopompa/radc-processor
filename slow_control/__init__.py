from data_parser.data_io import make_total_dataFrame_processed
from glob import glob
import data_parser.plotting as pl
import matplotlib.pyplot as plt
import plotly.express as px
from jinja2 import Template
import pandas as pd
import plotly.express as px
from udp_receiver.receiver_class import convert_seconds
from data_parser import Parameters
import numpy as np
from time import time, strftime, gmtime
from isegcontroller.commander import Commander
from isegcontroller.interpreter import Interpreter
from os.path import getctime
import numpy as np
import shutil
# based on https://plotly.com/python/interactive-html-export/


class Control():

    _base_path = "/data/DAQMeasurements"

    def __init__(self,
                 target_root=_base_path,
                 target_dir='.',
                 target_file=None,
                 output_html_path=r"/home/mnd/Desktop/slowControl/pages/",
                 input_template_path=r"/home/mnd/Software/radc-processor/slow_control/templates/"
                 ) -> None:

        self.target_root = target_root
        self.target_dir = target_dir
        self.target_file = target_file
        self.n_files = len(
            glob(f'{self.target_root}/{self.target_dir}/*.bin'))
        self.output_html_path = output_html_path
        self.input_template_path = input_template_path

        self.start()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, exc_traceback):
        exit()

    def getMetadata(self, df, file, previous_metadata=pd.DataFrame()):
        metadata = {}
        totalTime = df.Timestamp_s.iloc[-1] - df.Timestamp_s.iloc[0]
        metadata['Measurement'] = file.split(
            '.')[-3] if 'chunk' in file else file.split('.')[-2]
        metadata['Chunk'] = file.split('.')[-2] if 'chunk' in file else 0
        metadata['Time'] = strftime('%X',gmtime(df.Timestamp_s.iloc[-1]))
        metadata['Snippet rate'] = convert_units(len(df) / totalTime, 'Hz')
        metadata['Event rate'] = convert_units(
            len(set(df['Event_ID'])) / totalTime, 'Hz')
        metadata['Pulse detection efficiency (%)'] = len(
            df[df.AveragePulsePass]) / len(df) * 100
        metadata['Duplicate pulses (%)'] = df.attrs['duplicated_pulses_fraction'] * 100
        metadata['Corrupted snippets (%)'] = df.attrs['corrupted_snippets_fraction'] * 100
        small_df = pd.DataFrame(metadata, index=[0])
        df_info = pd.concat([previous_metadata, small_df])
        return df_info

    def getHVInfo(self):
        commander = Commander(
            '/home/mnd/Software/iseg-hv-controller/iseg_libs/default_config.toml')
        interpreter = Interpreter(commander)
        data = interpreter.get_info()
        df = pd.DataFrame(data)
        df['status'] = (df['status_v_limit_exceed'] == False) & (df['status_c_limit_exceed'] == False) & (df['status_current_trip'] == False)  \
            & (df['status_emergency'] == False)
        df['Status'] = ['OK' if s else 'PROBLEM' for s in df['status']]
        df['Address'] = [f'0.{(c-1)//16}.{(c-1)%16}' for c in df['channel_id']]
        status_on = df['status_on']
        df['Power'] = ['ON' if c else 'OFF' for c in status_on]

        # ensure correct type by replacing unread variables
        df.loc[df['control_v_set'] == '','control_v_set'] = 0
        df.loc[df['status_v_measure'] == '','status_v_measure'] = 0
        df.loc[df['control_c_set'] == '','control_c_set'] = 0
        df.loc[df['status_c_measure'] == '','status_c_measure'] = 0

        df['V_set'] = np.round(
            df['control_v_set'].astype(float, errors='ignore'), 2)
        df['V_meas'] = np.round(
            df['status_v_measure'].astype(float, errors='ignore'), 2)
        df['I_set (uA)'] = np.round(
            df['control_c_set'].astype(float, errors='ignore') * 10**6, 0)
        df['I_meas (uA)'] = np.round(
            df['status_c_measure'].astype(float, errors='ignore') * 10**6, 0)
        
        df['vs'] = [np.abs(df['V_set'][i]-df['V_meas'][i]) <
                    2 if df['Power'][i] == 'ON' else True for i in range(len(df))]
        df['Voltage status'] = ['OK' if c ==
                                True else 'PROBLEM' for c in df['vs']]
        df = df[['Address', 'Power', 'V_set', 'V_meas',
                 'I_set (uA)', 'I_meas (uA)', 'Status', 'Voltage status']]

        return df
    def generateHTMLFile(self,input_file,output_file,context):
        with open(self.output_html_path + output_file, "w", encoding="utf-8") as output_file:
            with open(self.input_template_path + input_file) as template_file:
                j2_template = Template(template_file.read())
                output_file.write(j2_template.render(context))

    def generate_plots(self, previous_metadata=pd.DataFrame(), file=None):
        print('Generating plots...')
        start = time()
        try:
            df_HV = self.getHVInfo()
        except:
            df_HV = pd.DataFrame({'Error':'Reading not possible'},index=[0])

        _, df = make_total_dataFrame_processed(file)
        df_info = self.getMetadata(df, file, previous_metadata)
        fig, ax = plt.subplots()
        pl.plotCountsPerChannel(df, ax)
        fig.savefig('/home/mnd/Desktop/slowControl/images/hCountsPerChannel.png')
        plt.close()
        fig = px.histogram(x=df['PulseTime_us'][df.AreaOverHeightPass == True], log_y=True)
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
        centerEnergy = df[(df.PulseTime_us < 0.15) & (
            df.PulseTime_us > -0.15)].groupby('Event_ID').ApproxEnergy_keVee.sum()
        beforeTriggerEnergy = df[df.PulseTime_us < -
                                 0.15].groupby('Event_ID').ApproxEnergy_keVee.sum()
        afterTriggerEnergy = df[df.PulseTime_us > 0.15].groupby(
            'Event_ID').ApproxEnergy_keVee.sum()

        fig_trigger = px.histogram(x=centerEnergy, log_y=True)
        fig_trigger.update_traces(xbins=dict(
            start=0,
            end=20000,
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

        tmp_df = pd.DataFrame(dict(
            series=np.concatenate(
                (["before"]*len(beforeTriggerEnergy), ["after"]*len(afterTriggerEnergy))),
            data=np.concatenate((beforeTriggerEnergy, afterTriggerEnergy)))
        )
        fig_comparison = px.histogram(
            tmp_df, x="data", color="series", barmode="overlay", log_y=True)
        fig_comparison.update_traces(xbins=dict(
            start=0,
            end=20000,
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
        topbar='''<div class="topnav">
        <a class="active" href="file:///home/mnd/Desktop/slowControl/pages/online_analysis.html">Home</a>
        <a class="active" href="file:///home/mnd/Desktop/slowControl/pages/high_voltage.html">High voltage</a>
        <a class="active" href="file:///home/mnd/Desktop/slowControl/pages/eventsPage.html">Events</a>
        <a class="active" href="file:///home/mnd/Desktop/slowControl/pages/pulsesPage.html">Pulses</a>
        </div>\n'''
        
        context = {
            "topbar":topbar,
            "fig": fig.to_html(full_html=False),
            "table": df_info[::-1].head(10).to_html(index=False, float_format="%.4g", justify='left'),
            "title": f"Analysis of file {file}",
            "fig_trigger": fig_trigger.to_html(full_html=False),
            "fig_comp": fig_comparison.to_html(full_html=False),
            "table_HV": df_HV.to_html(index=False, justify='left', float_format="%g")

        }

        context_HV = {
            "topbar":topbar,
            "title": f"Analysis of file {file}",
            "table_HV": df_HV.to_html(index=False, justify='left', float_format="%g")
        }

        eventsDir = f'/home/mnd/Desktop/slowControl/events'
        pulsesDir = f'/home/mnd/Desktop/slowControl/pulses'

        shutil.rmtree(eventsDir,ignore_errors=True)
        pl.plot_events_coincidence(df,save=True,outDir=eventsDir)
        
        shutil.rmtree(pulsesDir,ignore_errors=True)
        pl.plotEventsPulseFinder(df,save=True,outDir=pulsesDir)

        eventsImages = glob(f'{eventsDir}/*.pdf')
        pulsesImages = glob(f'{pulsesDir}/*.pdf')

        context_events = {
            "topbar":topbar,
            "title": f"Analysis of file {file}",
            "file_list":eventsImages
        }

        context_pulses = {
            "topbar":topbar,
            "title": f"Analysis of file {file}",
            "file_list":pulsesImages
        }

        self.generateHTMLFile("template.html","online_analysis.html",context)
        self.generateHTMLFile("template_HV.html","high_voltage.html",context_HV)
        self.generateHTMLFile("template_events.html","eventsPage.html",context_events)
        self.generateHTMLFile("template_events.html","pulsesPage.html",context_pulses)
        

        print(f"You can see the plots at file://{self.output_html_path}online_analysis.html")
        print(f'Processing time: {convert_seconds(time()-start)}\n\n')
        return df_info

    def start(self):
        print('Starting...')
        metadata = pd.DataFrame()
        if self.target_file is None and self.target_dir is not None:
            while True:
                files = glob(
                    f'{self.target_root}/{self.target_dir}/*.bin', recursive=True)
                latest_file = max(files, key=getctime)
                files.sort()
                print(f"Analyzing {latest_file}... ")
                metadata = self.generate_plots(
                    file=files[-1], previous_metadata=metadata)

        else:
            self.generate_plots(
                f'{self.target_root}/{self.target_dir}/{self.target_file}')

    def switch_file(self, file):
        # check for not existent file
        self.target_file = file
        self.generate_plots(file)


def convert_units(size, unit: str):
    prefixes = ['', 'k', 'M', 'G', 'T']
    units = [p + unit for p in prefixes]
    for x in units:
        if size < 1000.:
            return "%3.3f %s" % (size, x)
        size /= 1000.

    return size
