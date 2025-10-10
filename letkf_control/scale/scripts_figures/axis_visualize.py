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


def viz_axis (strday, strhour):
    filename = 'hydrometeoraxis_20250925_tchires_letkc_L1_negativeQonly_lamda099_psobs_target960error1_window1h_'+str(strday)+str(strhour)+'.txt'
    valueaxis = np.loadtxt(filename)
    filename = 'hydrometeoraxis_20250717_tchires_letkc_baseline_'+str(strday)+str(strhour)+'.txt'
    valueaxis2 = np.loadtxt(filename)
    #plt.imshow(valueaxis[:,0:200],cmap='seismic',origin='lower')
    vvmax=0.5
    vvmin=-0.5
    # {{change 1}}
    plt.figure(figsize=(8, 6))  # Adjust figure size (width, height) - height larger than width
    extent = [0, 500, 0, 20]  # [left, right, bottom, top]

    # Plot valueaxis
    plt.imshow(valueaxis2[:,0:100]*1000,cmap='seismic',origin='lower',interpolation='nearest', extent=extent, aspect=16.0, vmin=0.0, vmax=0.5)
    plt.colorbar()
    # {{change 2}}
    plt.xlabel('Distance (km)')
    plt.ylabel('Height (km)')
    plt.savefig('hydrometeoraxis_20250717_tchires_letkc_baseline_'+str(strday)+str(strhour)+'.png',dpi=300)
    plt.close()

    # Plot difference
    plt.figure(figsize=(8, 6))  # Adjust figure size (width, height) - height larger than width
    plt.imshow((valueaxis[:,0:100]-valueaxis2[0:,0:100])*1000,cmap='seismic',origin='lower',vmax=vvmax,vmin=vvmin, extent=extent, aspect=16.0)
    plt.colorbar()
    # {{change 3}}
    plt.xlabel('Distance (km)')
    plt.ylabel('Height (km)')
    plt.savefig('hydrometeoraxisdiff_20250925_tchires_letkc_L1_negativeQonly_lamda099_psobs_target960error1_window1h_'+str(strday)+str(strhour)+'.png',dpi=300)
    plt.close()




strday = "07"
strhour = "12"
viz_axis(strday, strhour)

strday = "08"
strhour = "00"
viz_axis(strday, strhour)

strday = "08"
strhour = "12"
viz_axis(strday, strhour)
strday = "09"
strhour = "00"
viz_axis(strday, strhour)
strday = "09"
strhour = "12"
viz_axis(strday, strhour)

