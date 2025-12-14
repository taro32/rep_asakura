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



# LETKF mdet
#baseline = '/work/jh220020o/f00019/scale_enkc/test_letkf_obsmake_20241004/result/case_tc/200001'
#workdir_letkf = '/work/jh220020o/f00019/scale_enkc/20241107_letkc_qvonly_noqc_local09_obserr01/result/case_tc/200001'
workdir_letkf = '/work/gv42/f00019/enkc_with_TC/20250918_tchires_letkc_L1_negativeQonly_lamda09_psobs_target960error1_window1h/result/tc_hires/200001'

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
valuename="QV"

# figure setting
vvmin=-1.0
vvmax=1.0
#vvmin=-1.0
#vvmax=1.0


#minpres_mdet = np.zeros((72))
#print(minpres_letkf)
interventioncount = np.zeros((verlevel,gridsize,gridsize))
diff = np.zeros((verlevel,gridsize,gridsize))
i = 0
for day in range(7,10):
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
        #pres = data.variables['PRES']
        #minpres_letkf[i] = np.min(pres[1,0,:,:],axis=(0,1))/100
        if i != 0:
            valueold = valuenew

        valuenew = data.variables[valuename]
        #minpres_letkf[i] = np.min(pres[1,:,:],axis=(0,1))/100
        #pres = data.variables['PRES']
        #minpres_mdet[i] = np.min(pres[1,0,:,:],axis=(0,1))/100
        
        if i != 0:
            diff += valuenew[0,:,:,:] - valueold[1,:,:,:]
            #diff[diff !=0.0] = 1
            #interventioncount += diff
        i += 1
colors = ["darkblue", "white"]
cmap_name = 'blue_to_white'
#colors = ["darkblue", "red"]
#cmap_name = 'blue_to_red'
cm = mcolors.LinearSegmentedColormap.from_list(cmap_name, colors, N=256)
fig = plt.figure()
plt.rcParams.update({'font.size': 14})  # Increase font size globally
ax = plt.gca()
#plt.imshow(interventioncount[0,:,:],cmap='seismic',interpolation='nearest',vmin=0,vmax=np.max(interventioncount[0,:,:]))
plt.imshow(diff[0,:,:]*1000,cmap=cm,interpolation='nearest',vmin=-8.0, vmax=0.0)#vmin=np.min(diff[0,:,:]*1000),vmax=0.0)
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
plt.savefig("totalvaporchange_20250918_tchires_letkc_L1_negativeQonly_lamda09_psobs_target960error1_window1h")
#plt.show()
sys.exit()

valueaxis = np.zeros((verlevel,gridsize))
valueaxiscount = np.zeros((verlevel,gridsize))
for i in range(0,gridsize):
    for j in range(0,gridsize):
        for k in range(0,verlevel):
            valueaxis[k,int(distance[i,j])]+=interventioncount[k,i,j]
            valueaxiscount[k,int(distance[i,j])]+=1
            print (i,j,k)
valueaxiscount [valueaxiscount == 0] = 1
valueaxis = valueaxis/valueaxiscount
#valueaxis = valueaxis
figure(figsize=(10,10))
#plt.imshow(valueaxis[:,0:200],cmap='seismic', vmin=0,vmax=1200,origin='lower')
#plt.imshow(valueaxis[:,0:200],cmap='seismic',vmin=0, vmax=10,origin='lower')
plt.plot(valueaxis[0,0:100])
#plt.colorbar()
plt.savefig('qvloc_20250925_tchires_letkc_L1_negativeQonly_lamda095_psobs_target960error1_window1h.png')
plt.show()


