# ... existing code ...
# {{change 1}}
import torch
#import netCDF4 as nc

gridsize = 400
verlevel = 40

# Precompute distances using PyTorch on the GPU
x, y = torch.meshgrid(torch.arange(gridsize), torch.arange(gridsize), indexing='ij')
x = x.float().cuda()
y = y.float().cuda()
center = gridsize / 2
distance = torch.sqrt((x - center)**2 + (y - center)**2).int()

# Create valueaxis and valueaxiscount tensors on the GPU
valueaxis = torch.zeros((verlevel, gridsize), dtype=torch.float32, device='cuda')
valueaxiscount = torch.zeros((verlevel, gridsize), dtype=torch.float32, device='cuda')

#strday = "09"
#strhour = "12"

# Use only one nc.Dataset call
filename=workdir_letkf+strday+strhour+'0000/hist_sno_np00064/mdet/history.pe000000.nc'
with nc.Dataset(filename,'r') as data:
    # Read the entire QV variable at once and transfer to GPU
    variable = torch.tensor(data.variables[valuename][0,:,:,:]).float().cuda()

    # Use PyTorch to accumulate values based on distance
    for k in range(0, verlevel):
        for i in range(0, gridsize):
            for j in range(0, gridsize):
                valueaxis[k, distance[i, j]] += variable[k, i, j]
                valueaxiscount[k, distance[i, j]] += variable[k, i, j] > 0 # Avoid adding 0

valueaxiscount[valueaxiscount == 0] = 1
valueaxis = valueaxis / valueaxiscount

# Transfer result back to CPU for plotting
valueaxis_cpu = valueaxis.cpu().numpy()

# ... existing code ...
#plt.imshow(valueaxis[:,0:200],cmap='seismic',origin='lower')
plt.imshow(valueaxis_cpu[:,0:200],cmap='seismic',origin='lower')
# ... existing code ...
