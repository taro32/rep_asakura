#
# Analyzing ensemble predictions
# created by Y.Sawada
#
#
from pylab import *
import numpy as np
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import numpy.ma as ma
import struct
import netCDF4 as nc
import matplotlib.colors as mcolors


#workdir = '/work/jh220020o/f00019/scale_enkc/test_fcst/result_exp20240624/case_tc/20000101000000/fcst_sno_np00004/'
#minpres = np.zeros((81,nens))
#for i in range(1,nens+1):
#    if i < 10:
#        stri = '000'+str(i)
#    elif i < 100:
#        stri = '00'+str(i)
#    elif i < 1000:
#        stri = '0'+str(i)
#    else:
#        stri = str(i)
#    data = nc.Dataset(workdir+stri+'/history.pe000000.nc','r')
#    pres = data.variables['PRES']
#    minpres[:,i-1] = np.min(pres[:,0,:,:],axis=(1,2))/100.0

#for i in range(0,nens):
#    if i == 95:
#        plt.plot(minpres[:,i],color='r')
#    else:
#        plt.plot(minpres[:,i],color='k')
#show()

# LETKF mdet
baseline = '/work/gv42/f00019/enkc_with_TC/20250717_tchires_letkc_baseline/result/tc_hires/200001'
#workdir_letkf = '/work/jh220020o/f00019/scale_enkc/20241107_letkc_qvonly_noqc_local09_obserr01/result/case_tc/200001'
workdir_letkf = '/work/gv42/f00019/enkc_with_TC/20250905_tchires_letkc_L1_negativeQonly_lamda09_psobs_target960error1_window1h/result/tc_hires/200001'

minpres_baseline = np.zeros((64))
minpres_mdet = np.zeros((64))
day = 1
hour = 0
i = 0


for day in range(4,10):
    if day < 10:
        strday = '0'+str(day)
    else:
        strday = str(day)
    for hour in range(0,24,3):
        if hour < 10:
            strhour = '0'+str(hour)
        else:
            strhour = str(hour)
        print('reading..... ', day, hour)
        data = nc.Dataset(baseline+strday+strhour+'0000/hist_sno_np00064/mdet/history.pe000000.nc','r')
        #data = nc.Dataset(workdir_letkf2+strday+strhour+'0000/hist_sno_np00004/mean/history.pe000000.nc','r')
        #pres = data.variables['PRES']
        #minpres_baseline[i] = np.min(pres[1,0,:,:],axis=(0,1))/100
        pres = data.variables['MSLP']
        minpres_baseline[i] = np.min(pres[0,:,:],axis=(0,1))/100
        if day < 7:
            data = nc.Dataset(baseline+strday+strhour+'0000/hist_sno_np00064/mdet/history.pe000000.nc','r')
        else:
            data = nc.Dataset(workdir_letkf+strday+strhour+'0000/hist_sno_np00064/mdet/history.pe000000.nc','r')    
        #data = nc.Dataset(workdir_letkf+strday+strhour+'0000/hist_sno_np00064/mdet/history.pe000000.nc','r')
        #pres = data.variables['PRES']
        #minpres_mdet[i] = np.min(pres[1,0,:,:],axis=(0,1))/100
        pres = data.variables['MSLP']
        minpres_mdet[i] = np.min(pres[0,:,:],axis=(0,1))/100
        i = i + 1

#plt.plot(minpres_baseline[:],color='black')
#plt.plot(minpres_mdet[:],color='green')
#plt.axvline(10, color='red',linestyle='--')
#plt.ylim(940,1000)
#plt.show()
#sys.exit()
day = 1
hour = 0
i = 0


# your target
#zlevel = 2
valuename="QV"

# figure setting
vvmin=-1.0
vvmax=1.0
#vvmin=-1.0
#vvmax=1.0

#colors = ["darkblue", "white"]
#cmap_name = 'blue_to_white'
colors = ["darkblue", "red"]
cmap_name = 'blue_to_red'
cm = mcolors.LinearSegmentedColormap.from_list(cmap_name, colors, N=256)

#minpres_letkf = np.zeros((72))
#minpres_mdet = np.zeros((72))
#print(minpres_letkf)
increment_big = np.zeros((600,600))
for day in range(7,10):
    if day < 10:
        strday = '0'+str(day)
    else:
        strday = str(day)
    for hour in range(0,24,1):
        if hour < 10:
            strhour = '0'+str(hour)
        else:
            strhour = str(hour)
        print('reading..... ', day, hour)
        data = nc.Dataset(workdir_letkf+strday+strhour+'0000/hist_sno_np00064/mdet/history.pe000000.nc','r')
        pres = data.variables['PRES']
        #minpres_letkf[i] = np.min(pres[1,0,:,:],axis=(0,1))/100
        if i != 0:
            valueold = valuenew

        valuenew = data.variables[valuename]
        #minpres_letkf[i] = np.min(pres[1,:,:],axis=(0,1))/100
        #pres = data.variables['PRES']
        #minpres_mdet[i] = np.min(pres[1,0,:,:],axis=(0,1))/100
        if i != 0:
            fig = plt.figure(figsize=(20,10))
            ax1 = fig.add_subplot(2,3,1)
            ax1.set_title("QV [g/kg]",fontsize=16)
            ax1.tick_params(labelsize=8)
            plt.imshow(valuenew[0,0,:,:]*1000, vmin=0, vmax=20.0)
            plt.colorbar(shrink=0.3)
            plt.gca().invert_yaxis()
            ax2 = fig.add_subplot(2,3,2)
            ax2.set_title("perturbation [g/kg] at lev 0",fontsize=16)
            increment = valuenew[0,0,:,:] - valueold[1,0,:,:]
            #increment_big[100:500,100:500] = increment
            #print(shape(increment_big))
            #plt.imshow(increment_big[0:600,0:600]*1000, vmin=vvmin, vmax=vvmax, cmap="seismic")
            plt.imshow(increment*1000, vmin=vvmin, vmax=vvmax, cmap="seismic")
            ax2.tick_params(labelsize=8)
            plt.colorbar(shrink=0.3)
            plt.gca().invert_yaxis()
            ax3 = fig.add_subplot(2,3,3)
            ax3.set_title("perturbation [g/kg] at lev 1",fontsize=16)
            increment = valuenew[0,1,:,:] - valueold[1,1,:,:]
            plt.imshow(increment*1000, vmin=vvmin, vmax=vvmax, cmap="seismic")
            ax3.tick_params(labelsize=8)
            plt.colorbar(shrink=0.3)
            plt.gca().invert_yaxis()
            #ax4 = fig.add_subplot(2,3,4)
            #ax4.set_title('central pressure [hPa]',fontsize=16)
            #plt.plot(minpres_baseline[:],color='black')
            #plt.plot(minpres_mdet[:],color='green')
            
            #plt.axvline(18 + i/3.0, color='red',linestyle='--')
            #plt.ylim(975,995)
            #plt.xlim(0,45)

            figname = "demo"+valuename+'_'+strday+strhour+'QV_lev0_1'
            plt.savefig('./demo_test_20250905_tchires_letkc_L1_negativeQonly_lamda09_psobs_target960error1_window1h/'+figname)
            plt.clf()
        i = i + 1
        #show()






