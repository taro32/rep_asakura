#
# Compare minimum sea level pressure
# nature: result_10, SNO output
# lambda = 0: result_1000, SNO output
#

from pylab import *
import os
import glob
import numpy as np
import matplotlib.pyplot as plt
import netCDF4 as nc


def dtime_string(day, hour):
    return f"200001{day:02d}{hour:02d}0000"


def read_min_mslp_from_files(files):
    if len(files) == 0:
        raise FileNotFoundError("No history files found")

    minpres = np.inf

    for f in files:
        with nc.Dataset(f, "r") as data:
            pres = data.variables["MSLP"]
            minpres = min(minpres, np.min(pres[0, :, :]) / 100.0)

    return minpres


def read_min_mslp_nature(workdir, day, hour):
    dtime = dtime_string(day, hour)
    hdir = os.path.join(workdir, dtime, "hist_sno_np00032", "mdet")
    files = sorted(glob.glob(os.path.join(hdir, "history.pe*.nc")))

    if len(files) == 0:
        raise FileNotFoundError(f"No nature files found in {hdir}")

    return read_min_mslp_from_files(files)


def read_min_mslp_lambda0(workdir, day, hour):
    dtime = dtime_string(day, hour)
    hdir = os.path.join(workdir, dtime, "hist_sno_np00032", "mdet")
    files = sorted(glob.glob(os.path.join(hdir, "history.pe*.nc")))

    if len(files) == 0:
        raise FileNotFoundError(f"No lambda=0 files found in {hdir}")

    return read_min_mslp_from_files(files)


def calculate_series(workdir_nature, workdir_lambda0, start_day, end_day):
    nt = (end_day - start_day + 1) * 8

    nature = np.full(nt, np.nan)
    lambda0 = np.full(nt, np.nan)

    i = 0
    for day in range(start_day, end_day + 1):
        for hour in range(0, 24, 3):
            if day == 9 and hour > 6:
                break

            print("reading..... ", f"{day:02d}", hour)

            try:
                nature[i] = read_min_mslp_nature(workdir_nature, day, hour)
            except FileNotFoundError as e:
                print("missing nature:", e)

            try:
                lambda0[i] = read_min_mslp_lambda0(workdir_lambda0, day, hour)
            except FileNotFoundError as e:
                print("missing lambda0:", e)

            i += 1

    return nature, lambda0


workdir_nature = "/work/gv42/v42013/20260603_enkc/result_10/case_tc"
workdir_lambda0 = "/work/gv42/v42013/20260603_enkc/result_1000/case_tc"

start_day = 7
end_day = 9

nature, lambda0 = calculate_series(
    workdir_nature,
    workdir_lambda0,
    start_day,
    end_day,
)

valid = ~np.isnan(nature) & ~np.isnan(lambda0)
nature = nature[valid]
lambda0 = lambda0[valid]

nt = len(nature)
x = np.arange(nt) * 3

plt.rcParams.update({"font.size": 14})

plt.plot(x, nature, color="black", label="nature", linewidth=3)
plt.plot(x, lambda0, color="tab:blue", label="$\\lambda$ = 0", linewidth=2)

plt.ylim(960, 1000)
plt.xlim(0, 54)
plt.xticks(np.arange(0, 55, 9))

plt.legend(fontsize="small", ncol=2)
plt.xlabel("Time [h]", fontsize=14)
plt.ylabel("MSLP (hPa)", fontsize=14)
plt.title("Minimum Sea Level Pressure", fontsize=16)

plt.tight_layout()
plt.savefig("minslp_nature_vs_lambda0.png", dpi=300, bbox_inches="tight")

print("nature")
print(nature)

print("lambda = 0")
print(lambda0)

plt.show()