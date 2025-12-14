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
filename = 'history/merged_history1.pe000000.nc'
print('reading...', filename)
data = nc.Dataset(filename,'r')



# your target
zlevel = 0 # height
time = 400 #timestamp
valuename="PT" # variables QV = water vapor


#value[time, z, y, x]

# visualization
value = data.variables[valuename]
fig = plt.figure(figsize=(20,20))
ax1 = fig.add_subplot(1,1,1)
plt.rcParams['axes.labelsize'] = 24
plt.rcParams['font.size'] = 24
ax1.set_title("QV [g/kg]",fontsize=24)
ax1.tick_params(labelsize=24)
plt.imshow(value[time,:15,60,:])
ax1.invert_yaxis()
plt.colorbar(shrink=0.3)
plt.savefig('./test_tc.png')






