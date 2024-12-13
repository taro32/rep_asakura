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



# LETKF mdet
#baseline = '/work/jh220020o/f00019/scale_enkc/test_letkf_obsmake_20241004/result/case_tc/200001'
#workdir_letkf = '/work/jh220020o/f00019/scale_enkc/20241107_letkc_qvonly_noqc_local09_obserr01/result/case_tc/200001'
workdir_letkf = '/work/gv42/f00019/enkc_with_TC/20241212_letkc_qvonly_noqc_local07anddist_target990/result/case_tc/200001'


distance = np.zeros((120,120))
for i in range(0,120):
    for j in range(0,120):
        distance[i,j] =  np.sqrt((i-60)**2 + (j-60)**2)
#plt.imshow(distance,cmap='seismic')
#plt.show()
#sys.exit()

#zlevel = 2
valuename="U"

# figure setting
vvmin=-1.0
vvmax=1.0
#vvmin=-1.0
#vvmax=1.0


#minpres_mdet = np.zeros((72))
#print(minpres_letkf)
interventioncount = np.zeros((20,120,120))
i = 0
for day in range(2,8):
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
            diff = valuenew[0,:,:,:] - valueold[1,:,:,:]
            diff[diff !=0.0] = 1
            interventioncount += diff
        i += 1

valueaxis = np.zeros((20,120))
valueaxiscount = np.zeros((20,120))
for i in range(0,120):
    for j in range(0,120):
        for k in range(0,20):
            valueaxis[k,int(distance[i,j])]+=interventioncount[k,i,j]
            valueaxiscount[k,int(distance[i,j])]+=1
valueaxiscount [valueaxiscount == 0] = 1
#valueaxis = valueaxis/valueaxiscount
plt.imshow(valueaxis[:,0:50],cmap='seismic', origin='lower')
plt.colorbar()
plt.show()


