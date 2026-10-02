import pandas as pd
import numpy as np
from time import time
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from scipy.special import factorial
from data_parser.Parameters import birksFunction
from data_parser.plotting import increaseTextSize
import os
from pathlib import Path


def birksLawSum(energies,birksFunction):
    quenchedEnergies = birksFunction
    (energies)
    return np.sum(quenchedEnergies)
        

start = time()

storageDir = '/nfs/almond/ALMOND/'
folder = 'neutronBackground_HallC'
energyColumn = 'ScaledEnergy_keVee'
conversionToNcm2s = 9.16
errConversionToNcm2s = 0.46
# PERSONALIZE THE DIRECTORY WHERE YOU STORE IMAGES
imageDir = '/users/p/pompafra/neutronBackground/images/'

timeInformationDir = f'{storageDir}/{folder}/reducedProcessedFiles/'




file = f'{storageDir}/{folder}/reducedProcessedFiles/reducedProcessed3MeVThreshold.pickle'
dataFolder = f'{storageDir}/{folder}'

longFile = f'{storageDir}/{folder}/reducedProcessedFiles/reducedProcessed.pickle'

if not os.path.exists(imageDir):
    print(f'The directory {imageDir} does not exist.\nCreate it or change it to the correct one.')
    exit()
if folder == 'neutronBackground_HallC':
    imageDir = f'{imageDir}/HallC/neutronBackground/'
elif 'sensitivity' in folder:
    imageDir = f'{imageDir}/GATOR/sensitivity/'
elif folder == 'neutronBackground_HallB':
    imageDir = f'{imageDir}/HallB/neutronBackground/'
elif folder == 'neutronBackground_GATOR':
    imageDir = f'{imageDir}/GATOR/neutronBackground/'
else:
    print(f'Folder {folder} not recognized. Please check the folder name.')
    exit()
p = Path(imageDir)
p.mkdir(parents=True, exist_ok=True)


dates_to_cut = ['1970-01-01','1970-01-02']
if folder == 'neutronBackground_GATOR':
        dates_to_cut = ['2025-05-27','2025-06-13']
elif folder == 'neutronBackground_HallC':
    dates_to_cut = ['2025-05-01','2025-08-24']
elif folder == 'sensitivity_GATOR':
    dates_to_cut = ['1970-01-01','1970-01-02']


try:
    days = pd.read_csv(f'/timeInformation_{folder}.csv')
    totalTime = days.EffectiveTime.values[0] / 86400.
except:
    print('Could not read the measurement duration from the csv file')
    exit()

print(f'Analyzing folder {folder}')
print(f'Measurement time (days): {totalTime:.2f}')

dates_to_cut = [pd.to_datetime(date).date() for date in dates_to_cut]

triggerRegion = [-1,1]
maxPulseTime_us = 100
distanceAccidentals = 0.016*5
sumEnergyThreshold = 4000
signalThreshold = 50
sumEnergyForRate = 2300

def makeSignalVsAccidentalPlot(neutron_candidates_rate, accidentals_rate,maxPulseTime_us=50,energyThreshold = 0,dates_to_cut=dates_to_cut,totalTime=totalTime):
    
    print(neutron_candidates_rate)
    fig, ax = plt.subplots(figsize=(10, 5))
    neutron_candidates_excluding_cut = neutron_candidates_rate[~neutron_candidates_rate['Date'].between(*dates_to_cut)]['Event_ID']
    mean_signal = np.sum(neutron_candidates_excluding_cut) / totalTime
    mean_background = np.sum(accidentals_rate['Event_ID'][~accidentals_rate['Date'].between(*dates_to_cut)]) / totalTime
    mean_signal_error = np.sqrt(mean_signal/totalTime)
    mean_background_error = np.sqrt(mean_background/totalTime)
    netNeutronRate = mean_signal - mean_background
    netNeutronRateError = np.sqrt(mean_signal_error**2 + mean_background_error**2)

    cut_hallB = neutron_candidates_rate['Date'] < pd.to_datetime('2030-06-01').date()

    # if 'HallB' in folder:
    #     cut_hallB = neutron_candidates_rate['Date'] < pd.to_datetime('2026-06-01').date()
    #     mean_signal = 5.08
    #     mean_signal_error= 0.18
    #     mean_background = 0.84
    #     mean_background_error = 0.07
    #     netNeutronRate = mean_signal - mean_background
    #     netNeutronRateError = np.sqrt(mean_signal_error**2 + mean_background_error**2)

    print(f'Mean signal rate: {mean_signal:.2f} +/- {mean_signal_error:.2f} events/day')
    print(f'Mean background rate: {mean_background:.2f} +/- {mean_background_error:.2f} events/day')
    print(f'Net neutron rate: {netNeutronRate:.2f} +/- {netNeutronRateError:.2f} events/day')
    print(f'Neutron flux: {netNeutronRate * conversionToNcm2s/10:.2f} +/- {netNeutronRateError * conversionToNcm2s/10:.2f} (stat) +/-  {netNeutronRate*errConversionToNcm2s/10:.2f} (sys) x 10^-7 cm^-2 s^-1')
    print(f'Total error neutron flux: {netNeutronRateError * conversionToNcm2s/10+netNeutronRate*errConversionToNcm2s/10:.2f} x 10^-7 cm^-2 s^-1')
    print(f'Total error neutron flux (quadrature): {np.sqrt( (netNeutronRateError * conversionToNcm2s/10)**2+(netNeutronRate*errConversionToNcm2s/10)**2):.2f} x 10^-7 cm^-2 s^-1')
    

    ax.plot(neutron_candidates_rate['Date'][cut_hallB],neutron_candidates_rate['Event_ID'][cut_hallB],'.',label='Signal region',color='blue')
    ax.axhline(mean_signal,color='blue',linestyle='--',label= f'Average signal: ({mean_signal:.2f}'r' $\pm$ 'f'{mean_signal_error:.2f}) events/day')
    ax.plot(accidentals_rate['Date'][cut_hallB],accidentals_rate['Event_ID'][cut_hallB],'.',label='Background region',color='orange')
    ax.axhline(mean_background,color='orange',linestyle='--', label= f'Average background: ({mean_background:.2f}'r' $\pm$ 'f'{mean_background_error:.2f}) events/day')
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    plt.gcf().autofmt_xdate()
    if neutron_candidates_rate['Date'].between(*dates_to_cut).any():
        datelist = pd.date_range(start=neutron_candidates_rate['Date'].min(),end="2026-01-31").to_series() 
        dates_to_cut_forGraph = [pd.to_datetime(date) for date in dates_to_cut]     
        ax.fill_between(datelist, 0, 1, where=datelist.between(*dates_to_cut_forGraph), color='yellow', alpha=0.5, transform=ax.get_xaxis_transform(),label='Excluded period')
    if 'GATOR' in folder:
        ax.set_title('Hall A')
    elif 'HallC' in folder:
        ax.set_title('Hall C')
    elif 'HallB' in folder:
        ax.set_title('Hall B')
    # ax.set_xticks(range(0,len(df_days)+3,5))
    ax.set_xlabel('Date')
    ax.set_ylabel('Events per calendar day')
    # Add a preliminary watermark for conference figures
    # ax.text(0.88, 0.95, 'Preliminary', transform=ax.transAxes,
    #     fontsize=20, color='grey', alpha=0.7, ha='center', va='top',
    #     fontweight='bold')
    # ax.set_ylim(0,max(neutron_candidates_rate['Event_ID'])*1.3)
    ax.set_ylim(-0.3)
    # ax.set_yscale('log')
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.27),
          ncol=2)#, shadow=True)
    # ax.get_xaxis().set_major_locator(mdates.DayLocator(interval=10))
    plt.tight_layout()
    fig.savefig(f'{imageDir}/hNeutronCandidatesVsAccidental_{maxPulseTime_us:.0f}us_{energyThreshold:.0f}keV_{folder.split("_")[-1]}.pdf')
    plt.show()
    plt.close()


def checkPoissonDistribution(neutron_candidates_rate,dates_to_cut=dates_to_cut,totalTime=totalTime):
    
    neutron_candidates_excluding_cut = neutron_candidates_rate[~neutron_candidates_rate['Date'].between(*dates_to_cut)]['Event_ID']
    mean_signal = np.sum(neutron_candidates_excluding_cut) / totalTime

    plt.hist(neutron_candidates_excluding_cut,bins=np.arange(-0.5,40.5,1),density=True,histtype='step')
    x = np.arange(0, 40)
    poisson = np.exp(-mean_signal) * mean_signal**x / factorial(x)
    plt.plot(x, poisson, 'r-', label='Poisson distribution')
    plt.xlabel('Events per day')
    plt.ylabel('Probability')
    plt.legend()
    plt.tight_layout()
    plt.savefig(f'{imageDir}/hPoissonDistribution_{folder.split("_")[-1]}.pdf')
    plt.show()
    plt.close()

def makeEnergyPlot(df,maxPulseTime_us=50):
    dates_to_cut = ['2025-05-27','2025-06-13']
    dates_to_cut = [pd.to_datetime(date) for date in dates_to_cut]
    df = df[df['Date'].between(*dates_to_cut) == False]
    binWidth=200

    cut_hallB = df['Date'] < pd.to_datetime('2030-06-01')
    
    if 'HallB' in folder:
        cut_hallB = df['Date'] < pd.to_datetime('2026-06-01')
    df = df[cut_hallB]

    df.loc[:,'birksCorrectedEnergy'] = [birksFunction(e) if e > signalThreshold else 0 for e in df[energyColumn] ]

    df_n = df[df.Event_ID.isin(eventsWithNeutronCandidates)]
    df_n = df_n[(df_n.PulseTime_us < triggerRegion[0])].reset_index(drop=True)
    signal_energies=df_n.groupby('Event_ID')['birksCorrectedEnergy'].agg('sum')

    df_acc = df[df.Event_ID.isin(eventsWithAccidentals)]
    df_acc = df_acc[(df_acc.PulseTime_us > triggerRegion[1])].reset_index(drop=True)
    accidental_energies = df_acc.groupby('Event_ID')['birksCorrectedEnergy'].agg('sum')
    

    # Get Event_IDs where max energy is above 1500 keV
    high_energy_signal_events = signal_energies[signal_energies > 6000].index
    high_energy_accidental_events = accidental_energies[accidental_energies > 6000].index
    highEnergyEvents = np.array([*high_energy_signal_events,*high_energy_accidental_events])
    if len(highEnergyEvents) > 0:
        highEnergyEvents = np.sort(highEnergyEvents)
        df_events = pd.DataFrame({'events':highEnergyEvents})
        df_events.to_csv(f'./highEnergyEventsGATOR/eventsList_{folder.split("_")[-1]}.csv',index=False)
    signal_energies = np.asarray(signal_energies, dtype=float)
    num_nans = np.isnan(signal_energies).sum()
    if num_nans:
        print(f'Warning: {num_nans} nans present in signal energies')
        signal_energies = signal_energies[~np.isnan(signal_energies)]
    bins=np.arange(0,6000+binWidth,binWidth)
    binWidths = np.diff(bins)
    
    ys,bin_edges=np.histogram(signal_energies,bins=bins)
    bin_centers =  0.5*(bin_edges[1:] + bin_edges[:-1])
    


    yb,_=np.histogram(accidental_energies,bins=bins)
    fig, ax = plt.subplots()
    ax.errorbar(bin_centers,ys ,np.sqrt(ys) ,binWidths/2,fmt='.', drawstyle = 'steps-mid',label='Signal region',color='blue')
        
    ax.errorbar(bin_centers,yb,np.sqrt(yb),binWidths/2,fmt='.', drawstyle = 'steps-mid',label='Background region',color='orange')
    ax.set_xlabel(r'Total energy release in proton recoils (keV)')
    ax.set_ylabel(f'Counts per {binWidth:.0f} keV')
    ax.legend()
    ax.set_xlim(bins[0],bins[-1])
    # ax.text(0.75, 0.75, 'Preliminary', transform=ax.transAxes,
    #         fontsize=20, color='grey', alpha=0.7, ha='center', va='top',
    #         fontweight='bold')
    plt.tight_layout()

    fig.savefig(f'{imageDir}/hEnergyOfNeutronCandidates_{maxPulseTime_us:.0f}us_{energyColumn}_{folder.split("_")[-1]}.pdf')
    plt.close(fig)
    bin_centers =  0.5*(bin_edges[1:] + bin_edges[:-1])

    df_info = pd.DataFrame({'bin_centers': bin_centers, 'Signal': ys, 'Background': yb})
    df_info.to_csv(f'{imageDir}/hSignalBackgroundEnergies_{maxPulseTime_us:.0f}us_{energyColumn}_{folder.split("_")[-1]}.csv', index=False)

    # background subtracted 
    fig, ax = plt.subplots()
    ax.errorbar(bin_centers,(ys-yb) ,np.sqrt(yb + ys),binWidths/2,fmt='.', drawstyle = 'steps-mid',color='blue')
    ax.set_xlabel(r'Total energy release in proton recoils (keV)')
    ax.set_ylabel(f'Counts per {binWidth:.0f} keV')
    ax.set_xlim(bins[0],bins[-1])
    # ax.text(0.75, 0.75, 'Preliminary', transform=ax.transAxes,
    #     fontsize=20, color='grey', alpha=0.7, ha='center', va='top',
    #     fontweight='bold')
    plt.tight_layout()

    fig.savefig(f'{imageDir}/hNeutronEnergyWithBackgroundSubtraction_{maxPulseTime_us:.0f}us_{energyColumn}_{folder.split("_")[-1]}.pdf')
    plt.close(fig)





df = pd.read_pickle(file)
print(f'Terminated reading files in {time() - start:.2f} seconds.')
print(f'Events in the dataframe: {df.Event_ID.nunique()}')
df.loc[:,'Date'] = pd.to_datetime(df.Timestamp_s, unit='s')

if 'HallC' in folder:
    df=df[df.Date > '2025-08-24'].reset_index(drop=True)
    print('In hall C folder')


df = df[df.AveragePulsePass]
df = df[df[energyColumn] > signalThreshold]
df.loc[:,'PulseTime_us'] = np.round(df.PulseTime_us,3)

isInSignalRegion = df.PulseTime_us.between(-maxPulseTime_us,triggerRegion[0])
# isInAccidentalRegion = df.PulseTime_us < -maxPulseTime_us
isInAccidentalRegion = df.PulseTime_us > triggerRegion[1]
isInTriggerRegion = df.PulseTime_us.between(-0.1,0.1)
df = df[df.PulseTime_us.between(-maxPulseTime_us,maxPulseTime_us)]




sum_energy_trigger = df.loc[isInTriggerRegion].groupby('Event_ID')[energyColumn].sum()
df['SumEnergyTrigger'] = df['Event_ID'].map(sum_energy_trigger).fillna(0)
sum_energy_signal = df.loc[isInSignalRegion].groupby('Event_ID')[energyColumn].sum()
df['SumEnergySignal'] = df['Event_ID'].map(sum_energy_signal).fillna(0)
sum_energy_acc = df.loc[isInAccidentalRegion].groupby('Event_ID')[energyColumn].sum()
df['SumEnergyAccidentals'] = df['Event_ID'].map(sum_energy_acc).fillna(0)
accidentalCoincidencePassForSignal = df.loc[isInSignalRegion].groupby('Event_ID')['PulseTime_us'].transform(lambda x: (np.max(x) - np.min(x)) < distanceAccidentals)
df['AccidentalCoincidencePassForSignal'] = df['Event_ID'].map(accidentalCoincidencePassForSignal).fillna(True,downcast=bool)
accidentalCoincidencePassForAccidentals = df.loc[isInAccidentalRegion].groupby('Event_ID')['PulseTime_us'].transform(lambda x: (np.max(x) - np.min(x)) < distanceAccidentals)
df['AccidentalCoincidencePassForAccidentals'] = df['Event_ID'].map(accidentalCoincidencePassForAccidentals).fillna(True,downcast=bool)


# I WOULD PROBABLY REPLACE SUMENERGYTRIGGER WITH THE ALREADY PRESENT TRIGGERENERGY
eventsWithNeutronCandidates = df[(df.SumEnergyTrigger > sumEnergyThreshold) & (df.SumEnergySignal > signalThreshold) & isInSignalRegion & df.AccidentalCoincidencePassForSignal].Event_ID
eventsWithAccidentals = df[(df.SumEnergyTrigger > sumEnergyThreshold) & (df.SumEnergyAccidentals > signalThreshold) & isInAccidentalRegion & df.AccidentalCoincidencePassForAccidentals ].Event_ID

all_dates = pd.Index(df['Date'].dt.date.unique(), name='Date')

neutron_candidates_rate = (
    df[df.Event_ID.isin(eventsWithNeutronCandidates)]
    .groupby(df['Date'].dt.date)['Event_ID']
    .nunique()
    .reindex(all_dates, fill_value=0)
    .reset_index()
)
accidentals_rate = (
    df[df.Event_ID.isin(eventsWithAccidentals)]
    .groupby(df['Date'].dt.date)['Event_ID']
    .nunique()
    .reindex(all_dates, fill_value=0)
    .reset_index()
)

makeSignalVsAccidentalPlot(neutron_candidates_rate, accidentals_rate,maxPulseTime_us,signalThreshold)
increaseTextSize()
makeEnergyPlot(df,maxPulseTime_us)
checkPoissonDistribution(neutron_candidates_rate)


print(f'Elapsed time: {time() - start:.2f} seconds.' )