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
#workdir_letkf1 = '/work/jh220020o/f00019/scale_enkc/test_letkf_obsmake_20241004/result/case_tc/200001'
workdir_letkf1 = '/work/gv42/f00019/enkc_with_TC/20241115_nocontrol_obserr01_denseob/result/case_tc/200001'
#workdir_letkf1 = '/work/jh220020o/f00019/scale_enkc/20241105_letkc_qvonly_noqc_local001/result/case_tc/200001'
#workdir_letkf2 = '/work/jh220020o/f00019/scale_enkc/test_letkc_20241104_qvonly_noqc_local08/result/case_tc/200001'
#workdir_letkf1 = '/work/gv42/f00019/enkc_with_TC/20241109_letkc_qvonly_noqc_local095_obserr01_withQ/result/case_tc/200001'
#workdir_letkf1 = '/work/gv42/f00019/enkc_with_TC/20241110_letkc_qvonly_noqc_local07_obserr01_withQ_infl145/result/case_tc/200001'
workdir_letkf2 = '/work/gv42/f00019/enkc_with_TC/20241124_letkc_qvonly_noqc_local095anddist_cerror10/result/case_tc/200001'
#workdir_letkf2 = '/work/gv42/f00019/enkc_with_TC/20241115_nocontrol_obserr01_denseob/result/case_tc/200001'
#workdir_letkf = '/work/jh220020o/f00019/scale_enkc/test_letkc_20241031_qvonly_noqc/result/case_tc/200001'
#workdir_letkf = '/work/jh220020o/f00019/scale_enkc/test_letkc_20241029/result/case_tc/200001'
day = 1
hour = 0
i = 0
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
        data = nc.Dataset(workdir_letkf1+strday+strhour+'0000/hist_sno_np00004/mdet/history.pe000000.nc','r')
        #data = nc.Dataset(workdir_letkf2+strday+strhour+'0000/hist_sno_np00004/mean/history.pe000000.nc','r')
        #pres = data.variables['PRES']
        #minpres_letkf[i] = np.min(pres[1,0,:,:],axis=(0,1))/100
        pres = data.variables['MSLP']
        minpres_letkf[i] = np.min(pres[1,:,:],axis=(0,1))/100
        data = nc.Dataset(workdir_letkf2+strday+strhour+'0000/hist_sno_np00004/mdet/history.pe000000.nc','r')
        #pres = data.variables['PRES']
        #minpres_mdet[i] = np.min(pres[1,0,:,:],axis=(0,1))/100
        pres = data.variables['MSLP']
        minpres_mdet[i] = np.min(pres[1,:,:],axis=(0,1))/100
        i = i + 1

plt.plot(minpres_letkf[:],color='blue')
plt.plot(minpres_mdet[:],color='green')
plt.ylim(940,1000)
#plt.savefig('TCpres_nocntlvscntl_local095.png')
#plt.savefig('TCpres_local07.png')
plt.show()





