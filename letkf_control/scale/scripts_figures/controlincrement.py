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

# LETKF mean
#workdir_letkf = '/work/jh220020o/f00019/scale_enkc/test_letkf_obsmake_20241004/result/case_tc/200001'
workdir_letkf = '/work/jh220020o/f00019/scale_enkc/20241108_letkc_qvonly_noqc_local095_obserr01/result/case_tc/200001'
day = 1
hour = 0
i = 0

# your target
zlevel = 1
valuename="QV"

# figure setting
vvmin=-0.0010
vvmax=0.0010
#vvmin=-1.0
#vvmax=1.0

minpres_letkf = np.zeros((72))
minpres_mdet = np.zeros((72))
print(minpres_letkf)
for day in range(2,10):
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
        data = nc.Dataset(workdir_letkf+strday+strhour+'0000/hist_sno_np00004/mdet/history.pe000000.nc','r')
        #pres = data.variables['PRES']
        #minpres_letkf[i] = np.min(pres[1,0,:,:],axis=(0,1))/100
        if i != 0:
            valueold = valuenew

        valuenew = data.variables[valuename]
        #minpres_letkf[i] = np.min(pres[1,:,:],axis=(0,1))/100
        #pres = data.variables['PRES']
        #minpres_mdet[i] = np.min(pres[1,0,:,:],axis=(0,1))/100
        if i != 0:
            increment = valuenew[0,zlevel,:,:] - valueold[1,zlevel,:,:]
            plt.imshow(increment, vmin=vvmin, vmax=vvmax, cmap='seismic')
            plt.colorbar()
            figname = "cntlincrement"+valuename+str(zlevel)+'_'+strday+strhour+'local095'
            plt.savefig(figname)
            plt.clf()
        i = i + 1
        #show()






