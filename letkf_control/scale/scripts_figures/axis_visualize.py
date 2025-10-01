#
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
#workdir_letkf = '/work/gv42/f00019/enkc_with_TC/20250925_tchires_letkc_L1_negativeQonly_lamda05_psobs_target960error1_window1h/result/tc_hires/200001'
filename = 'uvradialaxis_20250925_tchires_letkc_L1_negativeQonly_lamda05_psobs_target960error1_window1h.txt'
valueaxis = np.loadtxt(filename)
filename = 'uvradialaxis_20250717_tchires_letkc_baseline.txt'
valueaxis2 = np.loadtxt(filename)
#plt.imshow(valueaxis[:,0:200],cmap='seismic',origin='lower')
vvmax=1.0
vvmin=-1.0
#plt.imshow((valueaxis[:,0:100]-valueaxis2[0:,0:100])*1000,cmap='seismic',origin='lower',vmax=vvmax,vmin=vvmin)
plt.imshow(valueaxis[:,0:100]-valueaxis2[0:,0:100],cmap='seismic',origin='lower',vmax=10,vmin=-10)
plt.colorbar()
plt.savefig('uvradialdiff_20250925_tchires_letkc_L1_negativeQonly_lamda05_psobs_target960error1_window1h.png')
plt.show()



