#
#

from pylab import *
import numpy as np
import matplotlib.pyplot as plt
import numpy.ma as ma
import struct
from scipy.io import FortranFile

data = np.loadtxt('./env.txt')

nens = 101
mean = 0
std_dev = 0.1

# Parameters for a 2D array
num_rows = 13       # Number of rows
#num_cols = 2      # Number of columns

# Generate 2D array of random numbers
#random_matrix = np.random.normal(loc=mean, scale=std_dev, size=(num_rows, num_cols))

for i in range (0,nens):
    random_matrix = np.random.normal(loc=mean, scale=std_dev, size=num_rows)
    #print(random_matrix)
    copy = data
    copy[0:13,2] = copy[0:13,2] + random_matrix
    np.savetxt('./env_perturb'+str(i+1)+'.txt',copy)


