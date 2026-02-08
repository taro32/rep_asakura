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
import matplotlib.colors as mcolors


#workdir = '/work/jh220020o/f00019/scale_enkc/test_fcst/result_exp20240624/case_tc/20000101000000/fcst_sno_np00004/'
#minpres = np.zeros((81,nens))
#for i in range(1,nens+1):
#    if i < 10:
#        stri = '000'+str(i)
#    elif i < 100:
#        stri = '00'+str(i)
#    elif i < 1000:
#        stri = '0'+str(i)
#    else:
#        stri = str(i)
#    data = nc.Dataset(workdir+stri+'/history.pe000000.nc','r')
#    pres = data.variables['PRES']
#    minpres[:,i-1] = np.min(pres[:,0,:,:],axis=(1,2))/100.0

#for i in range(0,nens):
#    if i == 95:
#        plt.plot(minpres[:,i],color='r')
#    else:
#        plt.plot(minpres[:,i],color='k')
#show()

# LETKF mdet
baseline = '/work/gv42/f00019/enkc_with_TC/20250717_tchires_letkc_baseline/result/tc_hires/200001'
#workdir_letkf = '/work/jh220020o/f00019/scale_enkc/20241107_letkc_qvonly_noqc_local09_obserr01/result/case_tc/200001'
#workdir_letkf = '/work/gv42/f00019/enkc_with_TC/20250925_tchires_letkc_L1_negativeQonly_lamda08_psobs_target960error1_window1h/result/tc_hires/200001'
workdir_letkf = '/work/gv42/f00019/enkc_with_TC/20251216_tchires_letkc_L1_RI_lamda025_psobs_target990error1_window1h/result/tc_hires/200001'





day = 1
hour = 0
i = 0


# your target
#zlevel = 2
valuename="QV"

# figure setting
vvmin=-1.0
vvmax=0
#vvmin=-1.0
#vvmax=1.0

colors = ["darkblue", "white"]
cmap_name = 'blue_to_white'
#colors = ["darkblue", "red"]
#cmap_name = 'blue_to_red'
cm = mcolors.LinearSegmentedColormap.from_list(cmap_name, colors, N=256)

#minpres_letkf = np.zeros((72))
#minpres_mdet = np.zeros((72))
#print(minpres_letkf)
increment_big = np.zeros((600,600))
for day in range(4,7):
    if day < 10:
        strday = '0'+str(day)
    else:
        strday = str(day)
    for hour in range(0,24,1):
        if hour < 10:
            strhour = '0'+str(hour)
        else:
            strhour = str(hour)
        print('reading..... ', day, hour)
        data = nc.Dataset(workdir_letkf+strday+strhour+'0000/hist_sno_np00064/mdet/history.pe000000.nc','r')
        #minpres_letkf[i] = np.min(pres[1,0,:,:],axis=(0,1))/100
        if i != 0:
            valueold = valuenew

        valuenew = data.variables[valuename]
        wwind = data.variables['W']
        #minpres_letkf[i] = np.min(pres[1,:,:],axis=(0,1))/100
        #pres = data.variables['PRES']
        #minpres_mdet[i] = np.min(pres[1,0,:,:],axis=(0,1))/100
        if i != 0:
            fig = plt.figure()
            plt.rcParams.update({'font.size': 14})  # Increase font size globally
            ax = plt.gca()
            increment = valuenew[0,0,:,:] - valueold[1,0,:,:]
            #increment_big[100:500,100:500] = increment
            #print(shape(increment_big))
            #plt.imshow(increment_big[0:600,0:600]*1000, vmin=vvmin, vmax=vvmax, cmap="seismic")
            # Use imshow to display the wwind data
            #im = ax.imshow(wwind[0,20,:,:], origin='lower', cmap='jet',vmin=0,vmax=1.0) # You might need to adjust 'cmap'
            # Create contour lines
            contour_min = 1.0
            contour_max = 2.0
            num_levels = 2  # Number of contour levels between min and max
            # Generate contour levels
            levels = np.linspace(contour_min, contour_max, num_levels)
            contours = ax.contour(wwind[1,15,:,:], colors='k', levels=levels, origin='lower',vmin=0.5,vmax=1.0) # Adjust 'levels' as needed # t = 0 or 1?
            # Add contour labels (optional)
            ax.clabel(contours, inline=True, fontsize=8)
            plt.imshow(increment*1000, vmin=vvmin, vmax=vvmax, cmap=cm, interpolation='nearest')

            x_tick_distances = np.arange(0, 2001, 500) # Ticks at every 500 km
            y_tick_distances = np.arange(0, 2001, 500) # Ticks at every 500 km

            x_tick_positions = x_tick_distances / 5  # Convert distance to index
            y_tick_positions = y_tick_distances / 5  # Convert distance to index

            # Set x-axis limit
            # {{change 3}}
            ax.set_xlim(0, 400)
            ax.set_ylim(0, 400)

            # {{change 4}}
            ax.set_xticks(x_tick_positions)
            ax.set_yticks(y_tick_positions)


            # Generate x-axis tick labels (0 to 2000)
            # {{change 5}}
            x_tick_labels = [str(int(x)) for x in x_tick_distances]  # Convert distance to string
            y_tick_labels = [str(int(y)) for y in y_tick_distances]  # Convert distance to string

            # Set x-axis tick labels
            # {{change 6}}
            ax.set_xticklabels(x_tick_labels)
            ax.set_yticklabels(y_tick_labels)

            plt.colorbar(shrink=0.3)
            plt.xlabel('Distance (km)')
            plt.ylabel('Distance (km)')        
            #plt.gca().invert_yaxis()
            ax.grid(True, linestyle='--')

            


            figname = "case_convection2"+valuename+'_'+strday+strhour+'QV_lev0_1'
            plt.savefig('./demo_test_20251216_tchires_letkc_L1_RI_lamda025_psobs_target990error1_window1h/'+figname, dpi=300)
            plt.clf()
        i = i + 1
        #show()






