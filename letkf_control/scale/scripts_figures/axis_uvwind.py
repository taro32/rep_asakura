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
    angle = np.zeros((gridsize,gridsize))
    for i in range(0,gridsize):
        for j in range(0,gridsize):
            distance[i,j] =  int(np.sqrt((i-gridsize/2)**2 + (j-gridsize/2)**2))
            angle[i,j] = np.arctan2(i - gridsize/2, j - gridsize/2)

    valuename=["U","V"]

    vvmin=-1.0
    vvmax=1.0




    data = nc.Dataset(workdir_letkf+strday+strhour+'0000/hist_sno_np00064/mdet/history.pe000000.nc','r')
    uu = data.variables[valuename[0]][0,:,:,:]
    vv = data.variables[valuename[1]][0,:,:,:]
    valueaxis_radial = np.zeros((verlevel,gridsize))
    valueaxiscount_radial = np.zeros((verlevel,gridsize))
    valueaxis_tangential = np.zeros((verlevel,gridsize))
    valueaxiscount_tangential = np.zeros((verlevel,gridsize))
    for j in range(0,gridsize):
        print (j)
        for i in range(0,gridsize):
            for k in range(0,verlevel):
                valueaxis_radial[k,int(distance[i,j])]+= -np.sin(angle[i,j])*uu[k,i,j] + np.cos(angle[i,j])*vv[k,i,j]
                valueaxiscount_radial[k,int(distance[i,j])]+=1
                valueaxis_tangential[k,int(distance[i,j])]+= np.cos(angle[i,j])*uu[k,i,j] + np.sin(angle[i,j])*vv[k,i,j]
                valueaxiscount_tangential[k,int(distance[i,j])]+=1
            
    valueaxiscount_radial[valueaxiscount_radial == 0] = 1
    valueaxiscount_tangential[valueaxiscount_tangential == 0] = 1
    valueaxis_radial = valueaxis_radial/valueaxiscount_radial
    valueaxis_tangential = valueaxis_tangential/valueaxiscount_tangential

    figure(figsize=(10,10))

    np.savetxt('uvradialaxis_20250918_tchires_letkc_L1_negativeQonly_lamda09_psobs_target960error1_window1h'+str(strday)+str(strhour)+'.txt', valueaxis_radial)
    np.savetxt('uvtangentialaxis_20250918_tchires_letkc_L1_negativeQonly_lamda09_psobs_target960error1_window1h'+str(strday)+str(strhour)+'.txt', valueaxis_tangential)



    #plt.imshow(valueaxis_radial[:,0:200],cmap='seismic',origin='lower',vmax=20,vmin=-20)
    #plt.colorbar()

    #plt.savefig('uvradialaxis_20250717_tchires_letkc_baseline'+str(strday)+str(strhour)+'.png')
    #plt.close()

    #plt.imshow(valueaxis_tangential[:,0:200],cmap='seismic',origin='lower',vmax=10,vmin=-10)
    #plt.colorbar()
    #plt.savefig('uvtangentialaxis_20250717_tchires_letkc_baseline.png')
    #plt.savefig('uvtangentialaxis_20250717_tchires_letkc_baseline'+str(strday)+str(strhour)+'.png')


    #plt.close()


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
