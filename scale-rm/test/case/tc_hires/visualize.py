#
# Test script to view SCALE output
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


# SNO output
filename = 'history/merged_history1_p.pe000000.nc'
print('reading...', filename)
data = nc.Dataset(filename,'r')

print(data)

# your target
zlevel = 2 # height
time = 40 #timestamp
valuename='PRES' # variables QV = water vapor


# visualization
value = data.variables[valuename]
fig = plt.figure(figsize=(20,20))
ax1 = fig.add_subplot(1,1,1)
plt.rcParams['axes.labelsize'] = 24
plt.rcParams['font.size'] = 24
ax1.set_title("QV [g/kg]",fontsize=24)
ax1.tick_params(labelsize=24)
plt.imshow(value[time,zlevel,150:450,150:450]*1000)
plt.colorbar(shrink=0.3)
plt.savefig('./test_tc.png')






