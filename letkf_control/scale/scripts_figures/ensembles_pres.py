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


workdir = '/work/jh220020o/f00019/scale_enkc/test_fcst/result_exp20240624/case_tc/20000101000000/fcst_sno_np00004/'
nens = 100 # ensemble size
minpres = np.zeros((81,nens))
for i in range(1,nens+1):
    if i < 10:
        stri = '000'+str(i)
    elif i < 100:
        stri = '00'+str(i)
    elif i < 1000:
        stri = '0'+str(i)
    else:
        stri = str(i)
    data = nc.Dataset(workdir+stri+'/history.pe000000.nc','r')
    pres = data.variables['PRES']
    minpres[:,i-1] = np.min(pres[:,0,:,:],axis=(1,2))/100.0

for i in range(0,nens):
    if i == 95:
        plt.plot(minpres[:,i],color='r')
    else:
        plt.plot(minpres[:,i],color='k')
#show()

# LETKF mean
workdir_letkf = '/work/jh220020o/f00019/scale_enkc/test_fcst/result/case_tc/200001'
day = 1
hour = 0
i = 0
minpres_letkf = np.zeros((81,nens))
for day in range(1,10):
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
        data = nc.Dataset(workdir_letkf+strday+strhour+'0000/hist_sno_np00004/mean/history.pe000000.nc','r')
        pres = data.variables['PRES']
        minpres_letkf[i] = np.min(pres[1,0,:,:],axis=(0,1))/100
        i = i + 1
plt.plot(minpres_letkf[:],color='blue')
plt.ylim(900,1000)
plt.show()





