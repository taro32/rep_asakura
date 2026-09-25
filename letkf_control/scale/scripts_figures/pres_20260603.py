#
# Analyzing ensemble predictions
# created by Y.Sawada
#
# Minimum sea level pressure
#

from pylab import *
import os
import glob
import numpy as np
import matplotlib.pyplot as plt
import netCDF4 as nc


def history_dir(workdir, day, hour):
    dtime = f"200001{day:02d}{hour:02d}0000"
    return os.path.join(workdir, dtime, "hist", "mdet")


def read_min_mslp(workdir, day, hour):
    hdir = history_dir(workdir, day, hour)
    files = sorted(glob.glob(os.path.join(hdir, "history.pe*.nc")))

    if len(files) == 0:
        raise FileNotFoundError(f"No history.pe*.nc files found in {hdir}")

    minpres = np.inf

    for f in files:
        with nc.Dataset(f, "r") as data:
            pres = data.variables["MSLP"]
            minpres = min(minpres, np.min(pres[0, :, :]) / 100)

    return minpres


def calculate_min_pressure(workdir_letkf1, workdir_letkf2, start_day, end_day):
    nt = (end_day - start_day + 1) * 8
    minpres_letkf = np.zeros((nt))
    minpres_mdet = np.zeros((nt))

    i = 0
    for day in range(start_day, end_day + 1):
        for hour in range(0, 24, 3):
            print("reading..... ", f"{day:02d}", hour)

            minpres_letkf[i] = read_min_mslp(workdir_letkf1, day, hour)

            if day < 7:
                minpres_mdet[i] = read_min_mslp(workdir_letkf1, day, hour)
            else:
                minpres_mdet[i] = read_min_mslp(workdir_letkf2, day, hour)

            i += 1

    return minpres_letkf, minpres_mdet


workdir_letkf1 = "/work/gv42/v42013/20260603_enkc/result_1000/case_tc"

start_day = 7
end_day = 9
numexp = 1

nt = (end_day - start_day + 1) * 8
control = np.zeros((nt, numexp))

nature, control[:, 0] = calculate_min_pressure(
    workdir_letkf1,
    workdir_letkf1,
    start_day,
    end_day,
)

plt.rcParams.update({"font.size": 14})

plt.plot(nature[:], color="black", label="nature", linewidth=3)

labels = ["$\\lambda$ = 0"]

for i in range(0, numexp):
    plt.plot(control[:, i], label=labels[i])

plt.ylim(960, 1000)
plt.xlim(0, nt - 1)

plt.xticks(
    np.arange(0, nt, 3),
    np.arange(0, nt * 3, 9),
)

plt.legend(fontsize="small", ncol=2)
plt.xlabel("Time [h]", fontsize=14)
plt.ylabel("MSLP (hPa)", fontsize=14)
plt.title("Minimum Sea Level Pressure", fontsize=16)

plt.savefig("minslp_test.png", dpi=300)

print(nature)
print(control[:, 0])

plt.show()