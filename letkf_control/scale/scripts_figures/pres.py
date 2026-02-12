#
# Analyzing ensemble predictions
# created by Y.Sawada
#
# BIAS & RMSE
#
from pylab import *
import numpy as np
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import numpy.ma as ma
import struct
import netCDF4 as nc


def calculate_min_pressure(workdir_letkf1, workdir_letkf2, start_day, end_day):
    minpres_letkf = np.zeros((72))
    minpres_mdet = np.zeros((72))
    i = 0
    for day in range(start_day, end_day + 1):
        if day < 10:
            strday = '0' + str(day)
        else:
            strday = str(day)
        endhour = 24
        for hour in range(0, endhour, 3):
            if hour < 10:
                strhour = '0' + str(hour)
            else:
                strhour = str(hour)
            print('reading..... ', strday, hour)
            data = nc.Dataset(workdir_letkf1 + strday + strhour + '0000/hist_sno_np00064/mdet/history.pe000000.nc', 'r')
            pres = data.variables['MSLP']
            #pres = data.variables['PRES']
            minpres_letkf[i] = np.min(pres[0, :, :], axis=(0, 1)) / 100
            #minpres_letkf[i] = np.min(pres[0, 0, :, :], axis=(0, 1)) / 100

            if day < 7:
                data = nc.Dataset(workdir_letkf1 + strday + strhour + '0000/hist_sno_np00064/mdet/history.pe000000.nc', 'r')
            else:
                data = nc.Dataset(workdir_letkf2 + strday + strhour + '0000/hist_sno_np00064/mdet/history.pe000000.nc', 'r')
            pres = data.variables['MSLP']
            #pres = data.variables['PRES']
            minpres_mdet[i] = np.min(pres[0, :, :], axis=(0, 1)) / 100
            #minpres_mdet[i] = np.min(pres[0, 0, :, :], axis=(0, 1)) / 100
            i = i + 1
    return minpres_letkf, minpres_mdet


#workdir_letkf1 = '/work/gv42/f00019/enkc_with_TC/20250717_tchires_letkc_baseline/result/tc_hires/200001'
workdir_letkf1 = '/work/gv42/f00019/enkc_with_TC/20260209_tchires_letkc_baseline_revise/result/tc_hires/200001'

start_day = 8
end_day = 10
numexp = 5
control = np.zeros((72,numexp))
#workdir_letkf2 = '/work/gv42/f00019/enkc_with_TC/20250909_tchires_letkc_L1_negativeQonly_lamda00_psobs_target960error1_window1h/result/tc_hires/200001'
#nature, control[:,0] = calculate_min_pressure(workdir_letkf1, workdir_letkf2, start_day, end_day)
#workdir_letkf2 = '/work/gv42/f00019/enkc_with_TC/20250925_tchires_letkc_L1_negativeQonly_lamda05_psobs_target960error1_window1h/result/tc_hires/200001'
#nature, control[:,1] = calculate_min_pressure(workdir_letkf1, workdir_letkf2, start_day, end_day)
#workdir_letkf2 = '/work/gv42/f00019/enkc_with_TC/20250925_tchires_letkc_L1_negativeQonly_lamda08_psobs_target960error1_window1h/result/tc_hires/200001'
#nature, control[:,2] = calculate_min_pressure(workdir_letkf1, workdir_letkf2, start_day, end_day)
#workdir_letkf2 = '/work/gv42/f00019/enkc_with_TC/20250918_tchires_letkc_L1_negativeQonly_lamda09_psobs_target960error1_window1h/result/tc_hires/200001'
#nature, control[:,3] = calculate_min_pressure(workdir_letkf1, workdir_letkf2, start_day, end_day)
#workdir_letkf2 = '/work/gv42/f00019/enkc_with_TC/20250925_tchires_letkc_L1_negativeQonly_lamda0925_psobs_target960error1_window1h/result/tc_hires/200001'
#nature, control[:,4] = calculate_min_pressure(workdir_letkf1, workdir_letkf2, start_day, end_day)
#workdir_letkf2 = '/work/gv42/f00019/enkc_with_TC/20250925_tchires_letkc_L1_negativeQonly_lamda095_psobs_target960error1_window1h/result/tc_hires/200001'
#nature, control[:,5] = calculate_min_pressure(workdir_letkf1, workdir_letkf2, start_day, end_day)
#workdir_letkf2 = '/work/gv42/f00019/enkc_with_TC/20251012_tchires_letkc_L1_negativeQonly_lamda0975_psobs_target960error1_window1h/result/tc_hires/200001'
#nature, control[:,6] = calculate_min_pressure(workdir_letkf1, workdir_letkf2, start_day, end_day)
#workdir_letkf2 = '/work/gv42/f00019/enkc_with_TC/20251215_tchires_letkc_L1_RI_lamda00_psobs_target990error1_window1h/result/tc_hires/200001'
#workdir_letkf2 = '/work/gv42/f00019/enkc_with_TC/20251215_tchires_letkc_L1_RI_lamda00_psobs_target990error1_window1h/result/tc_hires/200001'
#nature, control[:,0] = calculate_min_pressure(workdir_letkf1, workdir_letkf2, start_day, end_day)
#workdir_letkf2 = '/work/gv42/f00019/enkc_with_TC/20251216_tchires_letkc_L1_RI_lamda025_psobs_target990error1_window1h/result/tc_hires/200001'
#nature, control[:,1] = calculate_min_pressure(workdir_letkf1, workdir_letkf2, start_day, end_day)
#workdir_letkf2 = '/work/gv42/f00019/enkc_with_TC/20251216_tchires_letkc_L1_RI_lamda05_psobs_target990error1_window1h/result/tc_hires/200001'
#nature, control[:,2] = calculate_min_pressure(workdir_letkf1, workdir_letkf2, start_day, end_day)
#workdir_letkf2 = '/work/gv42/f00019/enkc_with_TC/20251216_tchires_letkc_L1_RI_lamda08_psobs_target990error1_window1h/result/tc_hires/200001'
#nature, control[:,3] = calculate_min_pressure(workdir_letkf1, workdir_letkf2, start_day, end_day)

workdir_letkf2 = '/work/gv42/f00019/enkc_with_TC/20260210_tchires_letkc_L1_negativeQonly_lamda00_psobs_target960error1_window1h_revise/result/tc_hires/200001'
nature, control[:,0] = calculate_min_pressure(workdir_letkf1, workdir_letkf2, start_day, end_day)
workdir_letkf2 = '/work/gv42/f00019/enkc_with_TC/20260210_tchires_letkc_L1_negativeQonly_lamda05_psobs_target960error1_window1h_revise/result/tc_hires/200001'
nature, control[:,1] = calculate_min_pressure(workdir_letkf1, workdir_letkf2, start_day, end_day)
workdir_letkf2 = '/work/gv42/f00019/enkc_with_TC/20260210_tchires_letkc_L1_negativeQonly_lamda08_psobs_target960error1_window1h_revise/result/tc_hires/200001'
nature, control[:,2] = calculate_min_pressure(workdir_letkf1, workdir_letkf2, start_day, end_day)

workdir_letkf2 = '/work/gv42/f00019/enkc_with_TC/20260210_tchires_letkc_L1_negativeQonly_lamda09_psobs_target960error1_window1h_revise/result/tc_hires/200001'
nature, control[:,3] = calculate_min_pressure(workdir_letkf1, workdir_letkf2, start_day, end_day)

workdir_letkf2 = '/work/gv42/f00019/enkc_with_TC/20260210_tchires_letkc_L1_negativeQonly_lamda0925_psobs_target960error1_window1h_revise/result/tc_hires/200001'
nature, control[:,4] = calculate_min_pressure(workdir_letkf1, workdir_letkf2, start_day, end_day)


plt.rcParams.update({'font.size': 14})  # Increase font size globally
#print(minpres_letkf)
#print(minpres_mdet)
plt.plot(nature[:],color='black',label='nature',linewidth=3)
labels = ['$\\lambda$ = 0','$\\lambda$ = 0.5','$\\lambda$ = 0.8','$\\lambda$ = 0.9','$\\lambda$ = 0.925','$\\lambda$ = 0.95'] #,'$\\lambda$ = 0.975','$\\lambda$ = 0.99']
#labels = ['$\\lambda$ = 0.9','$\\lambda$ = 0.5','$\\lambda$ = 0.8','$\\lambda$ = 0.9','$\\lambda$ = 0.925','$\\lambda$ = 0.95'] #,'$\\lambda$ = 0.975','$\\lambda$ = 0.99']
#labels = ['$\\lambda$ = 0','$\\lambda$ = 0.25','$\\lambda$ = 0.5','$\\lambda$ = 0.8'] #,'$\\lambda$ = 0.975','$\\lambda$ = 0.99']
for i in range (0,numexp):
    plt.plot(control[:,i],label=labels[i])
    #plt.plot(control[:,i])
#plt.ylim(977,985)
#plt.ylim(950,985)
plt.ylim(975,982)
#plt.ylim(950,970)
#plt.xlim(25,47)
plt.xlim(0,23)
#plt.ylim(980,1000)
plt.xticks(np.arange(0, 23, 3), np.arange(0, 69, 9)) # Set x-axis ticks starting from 1
#plt.savefig('TCpres_nocntlvscntl_local095.png')
plt.legend(fontsize='small',ncol=2)  # Increase legend font size
plt.xlabel('Time [h]', fontsize=14) # increase axis label font size
plt.ylabel('MSLP (hPa)', fontsize=14) # increase axis label font size
plt.title('Minimum Sea Level Pressure', fontsize=16) # increase title font size
plt.savefig('minslp_revise.png',dpi=300)
plt.show()





