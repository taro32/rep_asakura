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
    filename = 'hydrometeoraxis_20250918_tchires_letkc_L1_negativeQonly_lamda09_psobs_target960error1_window1h_'+str(strday)+str(strhour)+'.txt'
    valueaxis = np.loadtxt(filename)
    filename = 'hydrometeoraxis_20250717_tchires_letkc_baseline_'+str(strday)+str(strhour)+'.txt'
    valueaxis2 = np.loadtxt(filename)
    filename = 'uvradialaxis_20250717_tchires_letkc_baseline'+str(strday)+str(strhour)+'.txt'
    valueaxis3 = np.loadtxt(filename)
    #plt.imshow(valueaxis[:,0:200],cmap='seismic',origin='lower')
    vvmax=0.5
    vvmin=-0.5
    # {{change 1}}
    plt.figure(figsize=(8, 6))  # Adjust figure size (width, height) - height larger than width
    extent = [0, 500, 0, 20]  # [left, right, bottom, top]

    # Plot valueaxis
    img = plt.imshow(valueaxis2[:,0:100]*1000,cmap='seismic',origin='lower',interpolation='nearest', extent=extent, aspect=16.0, vmin=0.0, vmax=0.5)
    plt.colorbar(img)
    # {{change 2}}
    # Overlay valueaxis3 as contours
    valueaxis3 = valueaxis3[:,0:100]
    x = np.linspace(extent[0], extent[1], valueaxis3.shape[1]) # create x values for contour
    y = np.linspace(extent[2], extent[3], valueaxis3.shape[0]) # create y values for contour
    X, Y = np.meshgrid(x, y)
    contour = plt.contour(X, Y, valueaxis3[:,0:100], colors='white', levels=np.arange(0, 40, 5))  # Adjust levels as needed, set colors to black
    plt.clabel(contour, inline=True, fontsize=8) # add labels to the contours

    plt.xlabel('Distance (km)')
    plt.ylabel('Height (km)')
    plt.savefig('hydrometeoraxis_withwind_20250717_tchires_letkc_baseline_'+str(strday)+str(strhour)+'.png',dpi=300)
    plt.close()

    # Plot difference
    filename = 'uvradialaxis_20250918_tchires_letkc_L1_negativeQonly_lamda09_psobs_target960error1_window1h'+str(strday)+str(strhour)+'.txt'
    valueaxis4 = np.loadtxt(filename)
    plt.figure(figsize=(8, 6))  # Adjust figure size (width, height) - height larger than width
    img = plt.imshow((valueaxis[:,0:100]-valueaxis2[0:,0:100])*1000,cmap='seismic',origin='lower',vmax=vvmax,vmin=vvmin, extent=extent, aspect=16.0)
    plt.colorbar(img)
    # {{change 3}}
    valueaxis4 = valueaxis4[:,0:100]
    x = np.linspace(extent[0], extent[1], valueaxis4.shape[1]) # create x values for contour
    y = np.linspace(extent[2], extent[3], valueaxis4.shape[0]) # create y values for contour
    X, Y = np.meshgrid(x, y)
    contour = plt.contour(X, Y, valueaxis4[:,0:100], colors='black', levels=np.arange(0, 40, 5))  # Adjust levels as needed, set colors to black
    plt.clabel(contour, inline=True, fontsize=8) # add labels to the contours


    plt.xlabel('Distance (km)')
    plt.ylabel('Height (km)')
    plt.savefig('hydrometeoraxisdiff_withwind_20250918_tchires_letkc_L1_negativeQonly_lamda09_psobs_target960error1_window1h_'+str(strday)+str(strhour)+'.png',dpi=300)
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

