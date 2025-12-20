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


def calc_axis (strday, strhour):
    workdir_letkf = '/work/gv42/f00019/enkc_with_TC/20250918_tchires_letkc_L1_negativeQonly_lamda09_psobs_target960error1_window1h/result/tc_hires/200001'

    gridsize = 400
    verlevel = 40
    distance = np.zeros((gridsize,gridsize))
    for i in range(0,gridsize):
        for j in range(0,gridsize):
            distance[i,j] =  int(np.sqrt((i-gridsize/2)**2 + (j-gridsize/2)**2))
    valuename="QV"


    vvmin=-1.0
    vvmax=1.0




    data = nc.Dataset(workdir_letkf+strday+strhour+'0000/hist_sno_np00064/mdet/history.pe000000.nc','r')
    variable = data.variables[valuename][0,:,:,:]
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
    np.savetxt('qvaxis_20250918_tchires_letkc_L1_negativeQonly_lamda09_psobs_target960error1_window1h_'+str(strday)+str(strhour)+'.txt', valueaxis)
    #np.savetxt('qvaxis_20250925_tchires_letkc_L1_negativeQonly_lamda05_psobs_target960error1_window1h.txt', valueaxis)

    #plt.imshow(valueaxis[:,0:200],cmap='seismic', vmin=0,vmax=1200,origin='lower')
    plt.imshow(valueaxis[:,0:200],cmap='seismic',origin='lower')
    plt.colorbar()
    plt.savefig('qvaxis_20250918_tchires_letkc_L1_negativeQonly_lamda09_psobs_target960error1_window1h_'+str(strday)+str(strhour)+'.png')
    #plt.savefig('qvaxis_20250925_tchires_letkc_L1_negativeQonly_lamda05_psobs_target960error1_window1h.png')
    plt.close()

strday = "07"
strhour = "12"
calc_axis(strday, strhour)

strday = "08"
strhour = "00"
calc_axis(strday, strhour)

strday = "08"
strhour = "12"
calc_axis(strday, strhour)
strday = "09"
strhour = "00"
calc_axis(strday, strhour)
strday = "09"
strhour = "12"
calc_axis(strday, strhour)