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


workdir = '/work/jh250035o/f00019/enkc_with_TC/20250616_fcst/result/tc_hires/20000101000000/fcst_sno_np00064/'
nens = 101 # ensemble size
minpres = np.zeros((81,nens))
print(workdir)
for i in range(1,nens+1):
    if i < 10:
        stri = '000'+str(i)
    elif i < 100:
        stri = '00'+str(i)
    elif i < 1000:
        stri = '0'+str(i)
    else:
        stri = str(i)
    #if i == 89:
    data = nc.Dataset(workdir+stri+'/history.pe000000.nc','r')
    #print("reading...", i)
    pres = data.variables['MSLP']
    #minpres[:,i-1] = np.min(pres[:,0,:,:],axis=(1,2))/100.0
    minpres[:,i-1] = np.min(pres[:,:,:],axis=(1,2))/100.0
    #minpres[60,i-1] = np.min(pres[60,0,:,:],axis=(0,1))/100.0

#print(minpres[60,80:100])
#plt.plot(minpres[60,80:100],color="k")
#plt.savefig("fcst_finalstate.png")
#plt.plot(minpres[:,88],color="r")
#plt.savefig("fcst_member0089")
#sys.exit()

for i in range(0,nens):
    if i == 88:
        plt.plot(minpres[:,i],color='r')
    else:
        plt.plot(minpres[:,i],color='k')
plt.savefig("fcst_20250616_mslp")
#show()
sys.exit()

# LETKF mean
workdir_letkf = '/work/jh220020o/f00019/scale_enkc/test_letkf_obsmake/result/case_tc/200001'
day = 1
hour = 0
i = 0
minpres_letkf = np.zeros((72,nens+1))
minpres_mdet = np.zeros((72))
print(minpres_letkf)
for day in range(1,9):
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
        minpres_letkf[i,0] = np.min(pres[1,0,:,:],axis=(0,1))/100
        for j in range(1,nens+1):
            if j < 10:
                strj = '000'+str(j)
            elif j < 100:
                strj = '00'+str(j)
            elif j < 1000:
                strj = '0'+str(j)
            else:
                strj = str(j)
            data = nc.Dataset(workdir_letkf+strday+strhour+'0000/hist_sno_np00004/'+strj+'/history.pe000000.nc','r')
            pres = data.variables['PRES']
            minpres_letkf[i,j] = np.min(pres[1,0,:,:],axis=(0,1))/100
        data = nc.Dataset(workdir_letkf+strday+strhour+'0000/hist_sno_np00004/mdet/history.pe000000.nc','r')
        pres = data.variables['PRES']
        minpres_mdet[i] = np.min(pres[1,0,:,:],axis=(0,1))/100
        i = i + 1

for j in range(0,nens):
    if j == 0:
        plt.plot(minpres_letkf[:,j],color='blue')
    else:
        plt.plot(minpres_letkf[:,j],color='k')

plt.plot(minpres_mdet[:],color='green')
plt.ylim(900,1000)
plt.savefig('TCpres.png')
plt.show()





