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
workdir_letkf = '/work/gv42/f00019/enkc_with_TC/20250717_tchires_letkc_baseline/result/tc_hires/200001'
#workdir_letkf = '/work/gv42/f00019/enkc_with_TC/20250925_tchires_letkc_L1_negativeQonly_lamda05_psobs_target960error1_window1h/result/tc_hires/200001'

gridsize = 400
verlevel = 40
distance = np.zeros((gridsize,gridsize))
for i in range(0,gridsize):
    for j in range(0,gridsize):
        distance[i,j] =  int(np.sqrt((i-gridsize/2)**2 + (j-gridsize/2)**2))
#plt.imshow(distance,cmap='seismic')
#plt.savefig("test.png")
#plt.show()
#sys.exit()

#zlevel = 2
valuename=["QC","QR","QI","QS","QG"]

# figure setting
vvmin=-1.0
vvmax=1.0
#vvmin=-1.0
#vvmax=1.0



strday = "08"
strhour = "00"
data = nc.Dataset(workdir_letkf+strday+strhour+'0000/hist_sno_np00064/mdet/history.pe000000.nc','r')
variable = np.zeros((verlevel,gridsize,gridsize))
for i in range(0,len(valuename)):
    variable += data.variables[valuename[i]][0,:,:,:]
valueaxis = np.zeros((verlevel,gridsize))
valueaxiscount = np.zeros((verlevel,gridsize))
for j in range(0,gridsize):
    print (j)
    for i in range(0,gridsize):
        for k in range(0,verlevel):
            valueaxis[k,int(distance[i,j])]+=variable[k,i,j]
            valueaxiscount[k,int(distance[i,j])]+=1
            
valueaxiscount [valueaxiscount == 0] = 1
valueaxis = valueaxis/valueaxiscount
#valueaxis = valueaxis
figure(figsize=(10,10))
np.savetxt('hydrometeoraxis_20250717_tchires_letkc_baseline.txt', valueaxis)
#np.savetxt('hydrometeoraxis_20250925_tchires_letkc_L1_negativeQonly_lamda05_psobs_target960error1_window1h.txt', valueaxis)

#plt.imshow(valueaxis[:,0:200],cmap='seismic', vmin=0,vmax=1200,origin='lower')
plt.imshow(valueaxis[:,0:200],cmap='seismic',origin='lower')
plt.colorbar()
plt.savefig('hydrometeoraxis_20250717_tchires_letkc_baseline.png')
#plt.savefig('hydrometeoraxis_20250925_tchires_letkc_L1_negativeQonly_lamda05_psobs_target960error1_window1h.png')
plt.show()



