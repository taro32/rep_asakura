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
    xx = np.linspace(0,399,400)
    yy = np.linspace(0,39,40)
    filename = 'uvtangentialaxis_20250717_tchires_letkc_baseline'+str(strday)+str(strhour)+'.txt'
    valueaxis1 = np.loadtxt(filename)
    filename = 'waxis_20250717_tchires_letkc_baseline_'+str(strday)+str(strhour)+'.txt'
    valueaxis2 = np.loadtxt(filename) * 20

    # Define different sampling intervals for x and y # {{add 1}}
    sample_interval_x = 5 # {{add 2}}
    sample_interval_y = 2 # {{add 3}}

    # Create a meshgrid for the coordinates
    X, Y = np.meshgrid(xx, yy)

    # {{change 1}}
    plt.figure(figsize=(8, 6))  # Adjust figure size (width, height) - height larger than width
    extent = [0, 500, 0, 20]  # [left, right, bottom, top]

    # Define the x range to visualize
    x_start = 0
    x_end = 100

    # Find the indices corresponding to the x range
    x_indices = np.where((xx >= x_start) & (xx <= x_end))[0]

    # Sample the data within the x range with specified intervals # {{change 1}}
    X_sampled = X[::sample_interval_y, x_indices[::sample_interval_x]] # {{add 4}}
    Y_sampled = Y[::sample_interval_y, x_indices[::sample_interval_x]] # {{add 5}}
    U_sampled = valueaxis1[::sample_interval_y, x_indices[::sample_interval_x]] # {{add 6}}
    V_sampled = valueaxis2[::sample_interval_y, x_indices[::sample_interval_x]] # {{add 7}}
    ref_speed = 1.0
    ref_length_cm = 1.0
    ref_length_in = ref_length_cm/2.54
    scale = ref_speed / ref_length_in
    plt.figure()
    ax = plt.gca()
    #print(xx)
    ax.quiver(X_sampled, Y_sampled, U_sampled, V_sampled, angles='xy', scale_units='xy', scale=scale, color='k')
    ax.set_xlim(0, 100)  # Keep the x-axis limit from 0 to 100 (original array indices)
    x_tick_positions = np.arange(0, 101, 20)  # Ticks at every 20 index points
    x_tick_labels = [str(int(x * 5)) for x in x_tick_positions]  # Convert index to distance and format as string
    ax.set_xticks(x_tick_positions)
    ax.set_xticklabels(x_tick_labels)
    ax.set_ylim(-1, 40)  # Keep the y-axis limit from 0 to 40 (original array indices)
    y_tick_positions = np.arange(0, 41, 10)  # Ticks at every 10 index points
    y_tick_labels = [str(x / 2) for x in y_tick_positions]  # Convert index to value
    ax.set_yticks(y_tick_positions)
    ax.set_yticklabels(y_tick_labels)

    ax.set_aspect(1.0)
    plt.xlabel('Distance (km)')
    plt.ylabel('Height (km)')

        # Place it near the top-left of the data area
    x0 = 90.0 #x.min() + 0.1*(x.max() - x.min())
    y0 = 1.0 #y.max() - 0.1*(y.max() - y.min())

    # A vector of magnitude == ref_speed (pointing east)
    u_ref, v_ref = ref_speed, 0.0

    ref = ax.quiver(
        x0, y0, u_ref, v_ref,
        scale_units="inches",
        scale=scale,
        angles="xy",
        width=0.006,    # slightly thicker so it stands out
        pivot="mid",
        color="red"
    )

    ax.annotate(
        f"{ref_speed} m/s",
        xy=(x0, y0), xycoords="data",
        xytext=(0, 6), textcoords="offset points",
        ha="center", va="bottom"
    )
    plt.savefig('2dwindaxis_20250717_tchires_letkc_baseline_'+str(strday)+str(strhour)+'.png')
    plt.close()

    filename = 'uvtangentialaxis_20250925_tchires_letkc_L1_negativeQonly_lamda099_psobs_target960error1_window1h'+str(strday)+str(strhour)+'.txt'
    valueaxis1_2 = np.loadtxt(filename)
    filename = 'waxis_20250925_tchires_letkc_L1_negativeQonly_lamda099_psobs_target960error1_window1h_'+str(strday)+str(strhour)+'.txt'
    valueaxis2_2 = np.loadtxt(filename) * 20

    plt.figure()
    ax = plt.gca()
    U_sampled_2 = valueaxis1_2[::sample_interval_y, x_indices[::sample_interval_x]] # {{add 6}}
    V_sampled_2 = valueaxis2_2[::sample_interval_y, x_indices[::sample_interval_x]] # {{add 7}}
    ref_speed = 1.0
    ref_length_cm = 1.0
    ref_length_in = ref_length_cm/2.54
    scale = ref_speed / ref_length_in
    q = ax.quiver(X_sampled, Y_sampled, U_sampled_2 - U_sampled, V_sampled_2 - V_sampled, angles='xy', scale_units='xy', scale=scale, color='k')
    #plt.colorbar(q, label="speed",extend='both')
    ax.set_xlim(0, 100)  # Keep the x-axis limit from 0 to 100 (original array indices)
    x_tick_positions = np.arange(0, 101, 20)  # Ticks at every 20 index points
    x_tick_labels = [str(int(x * 5)) for x in x_tick_positions]  # Convert index to distance and format as string
    ax.set_xticks(x_tick_positions)
    ax.set_xticklabels(x_tick_labels)
    ax.set_ylim(-1, 40)  # Keep the y-axis limit from 0 to 40 (original array indices)
    y_tick_positions = np.arange(0, 41, 10)  # Ticks at every 10 index points
    y_tick_labels = [str(x / 2) for x in y_tick_positions]  # Convert index to value
    ax.set_yticks(y_tick_positions)
    ax.set_yticklabels(y_tick_labels)
    ax.set_aspect(1.0)
    plt.xlabel('Distance (km)')
    plt.ylabel('Height (km)')
    # Place it near the top-left of the data area
    x0 = 90.0 #x.min() + 0.1*(x.max() - x.min())
    y0 = 1.0 #y.max() - 0.1*(y.max() - y.min())

    # A vector of magnitude == ref_speed (pointing east)
    u_ref, v_ref = ref_speed, 0.0

    ref = ax.quiver(
        x0, y0, u_ref, v_ref,
        scale_units="inches",
        scale=scale,
        angles="xy",
        width=0.006,    # slightly thicker so it stands out
        pivot="mid",
        color="red"
    )

    ax.annotate(
        f"{ref_speed} m/s",
        xy=(x0, y0), xycoords="data",
        xytext=(0, 6), textcoords="offset points",
        ha="center", va="bottom"
    )

# --------------------------------------------

    #ax.set_xlabel("x"); ax.set_ylabel("y")
    #ax.margins(0.05)
    #plt.tight_layout()

    plt.savefig('2dwindaxisdiff_20250925_tchires_letkc_L1_negativeQonly_lamda099_psobs_target960error1_window1h_'+str(strday)+str(strhour)+'.png')


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
