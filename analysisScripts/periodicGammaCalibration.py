import pandas as pd
import numpy as np
from glob import glob
import matplotlib.pyplot as plt
import ROOT # type: ignore
from scipy.interpolate import interp1d
from time import time
from pathlib import Path
import matplotlib.dates as mdates
from time import time, mktime
from datetime import datetime
from scipy.signal import find_peaks
import matplotlib

def increaseTextSize():
    matplotlib.rcParams.update({
    'font.size': 16,          # base size
    'axes.titlesize': 14,     # title
    'axes.labelsize': 14,     # x/y labels
    'xtick.labelsize': 12,    # tick labels
    'ytick.labelsize': 12,
    'legend.fontsize': 12     # legend
    })


increaseTextSize()

def fermiFunction(x,Q,B):
    return 1 / (1 + np.exp(-(x-Q)/B))

"""
This script must be executed in the singularity container
"""

start = time()

def manualCorrectionDataframe(df, folder):
    if folder == 'neutronBackground_HallC':
        df.loc[df.date.eq('2025-08-17') & df.channel.eq(0),'CF'] = df.loc[df.date.eq('2025-08-17') & df.channel.eq(0),'Fitted_CF'] 
        df.loc[df.date.eq('2025-08-17') & df.channel.eq(5),'CF'] = df.loc[df.date.eq('2025-08-17') & df.channel.eq(5),'Fitted_CF'] 
        df.loc[df.date.eq('2025-11-02') & df.channel.eq(7),'CF'] = df.loc[df.date.eq('2025-11-02') & df.channel.eq(7),'Fitted_CF'] 
        df.loc[df.date.eq('2025-08-17') & df.channel.eq(15),'CF'] = df.loc[df.date.eq('2025-08-17') & df.channel.eq(15),'Fitted_CF'] 
        df.loc[df.channel.eq(18),'CF'] = df.loc[df.channel.eq(18),'Fitted_CF'] 
        df.loc[df.channel.eq(25),'CF'] = df.loc[df.channel.eq(25),'Fitted_CF'] 
        df.loc[df.channel.eq(35),'CF'] = df.loc[df.channel.eq(35),'Fitted_CF']
    elif folder == 'neutronBackground_GATOR':
        df.loc[df.date.eq('2025-05-25') & df.channel.eq(0),'CF'] = df.loc[df.date.eq('2025-05-25') & df.channel.eq(0),'Fitted_CF'] 
        df.loc[df.date.eq('2025-06-15') & df.channel.eq(0),'CF'] = df.loc[df.date.eq('2025-06-15') & df.channel.eq(0),'Fitted_CF'] 
        df.loc[df.date.le('2025-06-14') & df.channel.eq(2),'CF'] = df.loc[df.date.le('2025-06-15') & df.channel.eq(2),'CF'] 
        df.loc[df.date.le('2025-05-04') & df.channel.eq(3),'CF'] = df.loc[df.date.le('2025-05-04') & df.channel.eq(3),'Fitted_CF'] 
        df.loc[df.date.le('2025-05-04') & df.channel.eq(6),'CF'] = df.loc[df.date.le('2025-05-04') & df.channel.eq(6),'Fitted_CF'] 
        df.loc[df.date.le('2025-05-04') & df.channel.eq(7),'CF'] = df.loc[df.date.le('2025-05-04') & df.channel.eq(7),'Fitted_CF'] 
        df.loc[df.date.le('2025-05-04') & df.channel.eq(8),'CF'] = df.loc[df.date.le('2025-05-04') & df.channel.eq(8),'Fitted_CF'] 
        df.loc[df.date.le('2025-05-04') & df.channel.eq(13),'CF'] = df.loc[df.date.le('2025-05-04') & df.channel.eq(13),'Fitted_CF'] 
        df.loc[df.date.le('2025-05-04') & df.channel.eq(15),'CF'] = df.loc[df.date.le('2025-05-04') & df.channel.eq(15),'Fitted_CF'] 
        df.loc[df.date.le('2025-05-04') & df.channel.eq(16),'CF'] = df.loc[df.date.le('2025-05-04') & df.channel.eq(16),'Fitted_CF'] 
        df.loc[df.date.le('2025-05-04') & df.channel.eq(18),'CF'] = df.loc[df.date.le('2025-05-04') & df.channel.eq(18),'Fitted_CF'] 
        df.loc[df.date.le('2025-05-04') & df.channel.eq(19),'CF'] = df.loc[df.date.le('2025-05-04') & df.channel.eq(19),'Fitted_CF'] 
        df.loc[df.date.le('2025-05-04') & df.channel.eq(22),'CF'] = df.loc[df.date.le('2025-05-04') & df.channel.eq(22),'Fitted_CF'] 
        df.loc[df.date.le('2025-05-04') & df.channel.eq(25),'CF'] = df.loc[df.date.le('2025-05-04') & df.channel.eq(25),'Fitted_CF'] 
        df.loc[df.date.le('2025-05-04') & df.channel.eq(27),'CF'] = df.loc[df.date.le('2025-05-04') & df.channel.eq(27),'Fitted_CF'] 
        df.loc[df.date.le('2025-05-04') & df.channel.eq(28),'CF'] = df.loc[df.date.le('2025-05-04') & df.channel.eq(28),'Fitted_CF'] 
        df.loc[df.date.le('2025-05-04') & df.channel.eq(29),'CF'] = df.loc[df.date.le('2025-05-04') & df.channel.eq(29),'Fitted_CF'] 
        df.loc[df.date.le('2025-05-04') & df.channel.eq(30),'CF'] = df.loc[df.date.le('2025-05-04') & df.channel.eq(30),'Fitted_CF'] 
        df.loc[df.date.le('2025-05-04') & df.channel.eq(31),'CF'] = df.loc[df.date.le('2025-05-04') & df.channel.eq(31),'Fitted_CF'] 
        df.loc[df.date.le('2025-05-04') & df.channel.eq(32),'CF'] = df.loc[df.date.le('2025-05-04') & df.channel.eq(32),'Fitted_CF'] 
    if len(df[df.CF.isna()]):
        print(df[df.CF.isna()][['date','channel','CF','Fitted_CF']])
        print('Warning: you are missing value of the Compton edges after manual correction')

        
        
    return df

    


def empirical_function(x,A,B,Q):
    return A / (1 + np.exp(B*(x-Q)))


def negativeGaussian(x, A, mu, sigma, C):
    return A * np.exp(-0.5 * ((x - mu) / sigma) ** 2) + C

def fitTimeSeries(df):
    res_cuts = [0.5,2.5]
    time_change_threshold = mktime(datetime.strptime('2025-05-09', '%Y-%m-%d').timetuple())
    cut_time=df['date_seconds'] > time_change_threshold 
    cut = cut_time & ~df.ExcessiveDifference
    try:
        pars = np.polyfit(df['date_seconds'][cut], df['CF'][cut], 2)
        corrected_cf = np.polyval(pars, df['date_seconds'])
        df.loc[:,'Fitted_CF']=corrected_cf
    except:
        df.loc[:,'Fitted_CF'] = df['CF'].mean()
    df.loc[:,'residuals'] = (df['CF'] - df['Fitted_CF']).abs() * 100
    # df.loc[df.residuals.between(*res_cuts),'Fitted_CF'] =  df.loc[df.residuals.between(*res_cuts),'CF']
    df.loc[~cut_time,'Fitted_CF'] = df['Fitted_CF'][cut_time].values[0]
    return df

def findOutliers(df):
    diff = (df['CF'] - df['CF'].shift(1)).abs()
    df.loc[:,'Difference'] = diff.fillna(0) * 100
    return df


def periodicGammaCalibration(folder = 'neutronBackground_HallC' ):

    mode = 'thallium' 
    E_th = 2615
    CE_th = 2*E_th**2/(2*E_th+511)
    fitLimits = [CE_th-150,CE_th+150] 
    binWidth = 25
    binWidth_derivative = 50
    saveFigures = True
    threshold_percentage = 1
    threshold_checkFit = 1
    min_distance_minima = 20
    homeDir = '/users/p/pompafra/'
    baseDir = '/nfs/almond/ALMOND/'
    gammaDir = f'{baseDir}/{folder}/gammaCalibration/'
    imageDir = f'{gammaDir}/gammaCalibrationResults/'
    p = Path(imageDir)
    p.mkdir(parents=True, exist_ok=True)

    negGauss = ROOT.TF1("gaussian", negativeGaussian, 2000, 2800, 4)
    empiricalFunction = ROOT.TF1("empiricalFunction", "[0] / (1 + TMath::Exp([1]*(x-[2])))", 0, 1e4)
    empiricalFunction.SetParameters(10000,0.05,2400)
    empiricalFunction.SetParLimits(0,0,1e4)
    empiricalFunction.SetParLimits(1,0,10)
    empiricalFunction.SetParLimits(2,2100,2500)
    empiricalFunction.SetParNames("A","B","Q")

    files = glob(f'{gammaDir}/*/*.pickle')
    print(gammaDir)
    files.sort()
    # files = files[-10:]

    results = []

    
            



    for f in files:
        date = f.split('/')[-2]
        df = pd.read_pickle(f)
        channel = int(f.split('/')[-1].replace('channel','').replace('.pickle',''))


        h, bins = np.histogram(df.ApproxEnergy_keVee,bins=np.arange(1700,2820,binWidth_derivative))

        bin_centers = 0.5*(bins[1:]+bins[:-1])
        derivative = np.gradient(h,bin_centers)*(bins[1]-bins[0])
        # Interpolate derivative for finer search of minimum
        interp_func = interp1d(bin_centers, derivative, kind='cubic')
        
        fine_bins = np.linspace(bin_centers[0], bin_centers[-1], 1000)
        fine_derivative = interp_func(fine_bins)

        fine_derivative_forFit = interp_func(fine_bins)
        min_idx = np.argmin(fine_derivative_forFit)

        # Find peaks in negative derivative
        peaks, _ = find_peaks(-fine_derivative_forFit, distance=min_distance_minima/((fine_bins[1]-fine_bins[0])))
        candidate_energies = fine_bins[peaks]
        
        if len(candidate_energies) < 1:
            print('Found no peaks')
        elif np.min(candidate_energies-CE_th) > 150:
            print(f'Found peaks at {candidate_energies}')

        # Select the one closest to CE_th
        if len(candidate_energies) > 0:
            min_energy = candidate_energies[np.argmin(np.abs(candidate_energies - CE_th))]
        else:
            min_energy = fine_bins[min_idx]
        min_energy = fine_bins[min_idx]
        

        
        hROOT = ROOT.TH1D(f'hGammaCalibration_ch{channel}_{date}',f'hGammaCalibration_ch{channel}_{date}',int((2800-1700)/binWidth),1700,2800)
        # c = ROOT.TCanvas(f'cGammaCalibration_ch{i}_{date}',f'cGammaCalibration_ch{i}_{date}',800,600)
        for i,e in enumerate(df.ApproxEnergy_keVee):
            hROOT.Fill(e)
        res=hROOT.Fit("empiricalFunction","LMERSQ","",min_energy-100,min_energy+100)
        Q = empiricalFunction.GetParameter(2)
        
        
        # print(f'Channel {channel} - {date}: Minimum of derivative at {min_energy:.1f} keV')
        # print(f'Channel {channel} - {date}: Q from ROOT fit = {Q:.1f} keV')
        # print(f'Difference = {abs(Q-min_energy)/Q:.3%}')
        # pars, _ = curve_fit(empirical_function, bin_centers, derivative, p0=[-1000,0.05,2400],)
        energies = np.arange(min_energy-100,min_energy+100,1)
        fittedFunction = empirical_function(energies, empiricalFunction.GetParameter(0),empiricalFunction.GetParameter(1),empiricalFunction.GetParameter(2))
        if saveFigures:
            fig, ax = plt.subplots(figsize=(11,6))
            ax.plot(bin_centers,h,'.',label='Energy spectrum',color='blue')
            ax.plot(bin_centers,derivative,'.',label='Derivative',color='orange')
            ax.plot(fine_bins,fine_derivative,'-',label='Interpolated derivative',color='black')
            ax.plot(energies,fittedFunction*binWidth_derivative/binWidth,'-',label='Fit')

            y_fit = empirical_function(np.array([Q]), empiricalFunction.GetParameter(0), empiricalFunction.GetParameter(1), empiricalFunction.GetParameter(2))[0] * binWidth_derivative / binWidth
            y_derivative = interp_func(min_energy)
            ax.plot([Q], [y_fit], marker='^',linestyle='', color='r', label=f'Empirical fit: {Q:.0f} 'r'keV$_{\rm ee}$')
            ax.plot([min_energy], [y_derivative], marker='^', linestyle='', color='g', label=f'Minimum of the derivative: {min_energy:.0f} 'r'keV$_{\rm ee}$')
            ax.set_xlabel(r'Energy (keV$_{\rm ee}$)')
            ax.set_ylabel('Counts')
            ax.set_title(f'Channel {channel} - {date}')
            fig.tight_layout()
            ax.grid()
            # l=plt.legend(title = f'Entries: {len(df)}\nRelative difference: {np.abs(Q-min_energy)/Q:.3%}')
            l=plt.legend(fontsize=11)
            fig.savefig(f'{imageDir}/hGammaCalibration_ch{channel}_{date}.pdf')
            plt.close()

        fitResults = {'channel':channel,'date':date,'Q_Root':Q,'Min_derivative':min_energy,'Rel_difference_%':np.abs(Q-min_energy)/Q*100,'AverageEnergy': (Q+min_energy)/2,'CF': ((Q+min_energy)/2)/CE_th ,'chi2':res.Chi2(),'ndf':res.Ndf(),'ExcessiveDifference':np.abs(Q-min_energy)/Q*100>threshold_percentage}
        if fitResults['ExcessiveDifference']:
            if np.abs(min_energy-CE_th) < np.abs(Q-CE_th):
                fitResults['AverageEnergy'] = min_energy
            else:
                fitResults['AverageEnergy'] = Q
            fitResults['CF'] = fitResults['AverageEnergy'] / CE_th
        results.append(fitResults)




    results.sort(key=lambda x: (x['channel'], x['date']))
    results_df = pd.DataFrame(results)
    results_df = results_df.reset_index(drop=True)
    results_df = results_df.groupby('channel').apply(findOutliers).reset_index(drop=True)
    fig,ax = plt.subplots()
    ax.hist(results_df['Difference'][results_df['Difference'] != 0],bins=np.arange(0,10,0.2),histtype='step')
    ax.set_xlabel('Difference to neighbor point (%)')
    ax.set_ylabel('Counts')
    fig.savefig(f'{imageDir}/hDifferences_{folder}.pdf')
    fig.savefig(f'./images/hDifferences_{folder}.pdf')
    plt.close(fig)

    results_df.loc[:,'Outlier'] = False
    results_df.loc[results_df['Difference'] > 1.5,'Outlier'] = True

    if folder == 'sensitivity_GATOR':
        results_df.to_csv(f'{imageDir}/gammaCalibrationResults_{folder}.csv',index=False,float_format='%.4f')
        print('Skipping the fitting of the correction factors...')
        exit(-1)


    results_df.loc[:,'date_seconds'] = results_df['date'].apply(lambda x: mktime(datetime.strptime(x, '%Y-%m-%d').timetuple()))
    results_df=results_df.groupby('channel').apply(fitTimeSeries).reset_index(drop=True)

    for c in range(36):
        df_channel = results_df[results_df.channel==c]
        fig, ax = plt.subplots()
        ax.plot(pd.to_datetime(df_channel['date'],format='%Y-%m-%d') + pd.DateOffset(months=1),df_channel.CF,'.-',color='blue')
        ax.plot(pd.to_datetime(df_channel['date'],format='%Y-%m-%d') + pd.DateOffset(months=1),df_channel.Fitted_CF,'-',label='Polynomial fit',color='orange')
        if 'GATOR' in folder:
            ax.axvline(pd.to_datetime('2025-05-09',format='%Y-%m-%d')+pd.DateOffset(months=1),color='r',linestyle='--',label='Change of threshold')
        ax.set_ylabel('Ratio to nominal Compton edge')
        ax.set_xlabel('Date')
        ax.set_title(f'Channel {c} - {mode} line')
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
        ax.xaxis.set_major_locator(mdates.MonthLocator(interval=1))
        ax.set_ylim(0.9,1.05)
        plt.grid()
        if df_channel['ExcessiveDifference'].any():
            ax.plot(pd.to_datetime(df_channel['date'][df_channel['ExcessiveDifference']],format='%Y-%m-%d')+ pd.DateOffset(months=1),df_channel.CF[df_channel['ExcessiveDifference']],'.',label='Incompatible fits',color='red',markersize=10)
        # if df_channel['Outlier'].any():
        #     ax.plot(pd.to_datetime(df_channel['date'][df_channel['Outlier']],format='%Y-%m-%d')+ pd.DateOffset(months=1),df_channel.CF[df_channel['Outlier']],'.',label='Outliers',color='green',markersize=10)
        
        plt.legend()
        plt.tight_layout()
        fig.savefig(f'{imageDir}/CF_timeDependence_ch{c}_{folder}.pdf')
        fig.savefig(f'{homeDir}/ALMOND/neutronBackground/images/GATOR/neutronBackground/CE_timeDependence/CF_timeDependence_ch{c}_{folder}.pdf')
        if folder=='test':
            fig.savefig(f'./testGammaCalibration/CF_timeDependence_ch{c}_{folder}.pdf')
        plt.close()

    fig, ax = plt.subplots()
    ax.hist(results_df['Rel_difference_%'],bins=np.arange(0,5,0.1),histtype='step')
    ax.set_ylabel('Counts')
    ax.set_xlabel('Relative difference between methods (%)')
    fig.savefig(f'{imageDir}/RelativeDifference_gammaCalibration_{folder}.pdf')
    fig.savefig(f'{homeDir}/ALMOND/neutronBackground/images/GATOR/neutronBackground/CE_timeDependence/timeDependence_{folder}.pdf')
    if folder=='test':
        fig.savefig(f'./testGammaCalibration/RelativeDifference_gammaCalibration_{folder}.pdf')




    results_df = manualCorrectionDataframe(results_df,folder)

    results_df.to_csv(f'{imageDir}/gammaCalibrationResults_{folder}.csv',index=False,float_format='%.4f')
    


    print(f'Completed periodic calibration of the {mode} line')
    print(f'Energy of the line: {E_th:.2f} keV')
    print(f'Energy of the Compton edge: {CE_th:.2f} keV')
    print(f'Fit limits: {fitLimits} keV')
    print(f'\n\nFraction of excessive differences: {np.sum(results_df.ExcessiveDifference)/len(results_df):.2%}')

    print(f'Elapsed time: {time()-start:.1f} seconds')


if __name__ == "__main__":
    periodicGammaCalibration(folder = 'neutronBackground_HallB' )