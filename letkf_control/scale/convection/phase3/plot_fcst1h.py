#!/usr/bin/env python3
"""Phase 3 の単独予報（1 member × 1 時間）の結果を図にする。

144 プロセス分の history（各 10 × 10 格子）をつなげて 120 × 120 格子に戻し、
次の 3 枚の図を出す。

  fcst1h_maps.png        : 地上降水・高度約 2 km の鉛直流・可降水量の水平分布（10, 30, 60 分）
  fcst1h_timeseries.png  : 領域平均・最大値の時間変化
  fcst1h_profiles.png    : 領域平均の鉛直分布（1 分と 60 分）

使い方: python3 plot_fcst1h.py [member 番号（既定 1）]
"""
import glob
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from netCDF4 import Dataset

MEM = sys.argv[1] if len(sys.argv) > 1 else "1"
OUT = "/work/gv42/v42013/20260923_enkc_convection/result/phase3_fcst1h"
HIST = f"{OUT}/history/{MEM}"
FIGDIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs", "phase3", "figs")
DX = 2000.0          # 格子間隔 [m]
NX = NY = 120        # 全体の格子数
Z_W = 2000.0         # 鉛直流を描く高さ [m]

files = sorted(glob.glob(f"{HIST}/history_*.pe*.nc"))
if len(files) != 144:
    sys.exit(f"history ファイルが {len(files)} 個しかない（144 個必要）: {HIST}")

with Dataset(files[0]) as d:
    time_min = d.variables["time"][:] / 60.0
    z = d.variables["z"][:]
nt, nz = len(time_min), len(z)
kw = int(np.argmin(np.abs(z - Z_W)))

# 全体の配列を用意して、各プロセスのタイルを x, y 座標の位置に入れる
prec = np.zeros((nt, NY, NX))
pw = np.zeros((nt, NY, NX))
t2 = np.zeros((nt, NY, NX))
olr = np.zeros((nt, NY, NX))
lwat = np.zeros((nt, NY, NX))        # 土壌水分（最上層）
w_k = np.zeros((nt, NY, NX))         # 高度 Z_W の鉛直流
wmax_col = np.zeros((nt, NY, NX))    # 鉛直方向の最大上昇流
qhyd_col = np.zeros((nt, NY, NX))    # 鉛直方向の最大水物質
pt_sum = np.zeros((nt, nz))
qv_sum = np.zeros((nt, nz))
qhyd_sum = np.zeros((nt, nz))

for f in files:
    with Dataset(f) as d:
        ix = np.rint((d.variables["x"][:] - DX / 2) / DX).astype(int)
        iy = np.rint((d.variables["y"][:] - DX / 2) / DX).astype(int)
        sl = (slice(None), slice(iy[0], iy[-1] + 1), slice(ix[0], ix[-1] + 1))
        prec[sl] = d.variables["PREC"][:] * 3600.0          # kg/m2/s -> mm/h
        pw[sl] = d.variables["PW"][:] / 1000.0               # g/m2 -> kg/m2
        t2[sl] = d.variables["T2"][:]
        olr[sl] = d.variables["OLR"][:]
        lwat[sl] = d.variables["LAND_WATER"][:, 0]
        w = d.variables["W"][:]
        w_k[sl] = w[:, kw]
        wmax_col[sl] = w.max(axis=1)
        qh = d.variables["QHYD"][:]
        qhyd_col[sl] = qh.max(axis=1) * 1e3                  # kg/kg -> g/kg
        pt_sum += d.variables["PT"][:].sum(axis=(2, 3))
        qv_sum += d.variables["QV"][:].sum(axis=(2, 3))
        qhyd_sum += qh.sum(axis=(2, 3))

npts = NX * NY
pt_mean, qv_mean, qhyd_mean = pt_sum / npts, qv_sum / npts * 1e3, qhyd_sum / npts * 1e3
os.makedirs(FIGDIR, exist_ok=True)
xkm = (np.arange(NX) + 0.5) * DX / 1e3
ext = [0, NX * DX / 1e3, 0, NY * DX / 1e3]
ink, muted = "#1f2328", "#6e7781"
plt.rcParams.update({"font.size": 9, "axes.edgecolor": muted, "axes.labelcolor": ink,
                     "xtick.color": muted, "ytick.color": muted, "axes.titlesize": 10})

# ---- 図 1: 水平分布 ----------------------------------------------------------
times = [10, 30, 60]
its = [int(np.argmin(np.abs(time_min - t))) for t in times]
rows = [
    ("Surface precipitation [mm/h]", prec, "Blues", 0, max(1.0, np.percentile(prec, 99.9))),
    (f"W at z = {z[kw]/1e3:.1f} km [m/s]", w_k, "RdBu_r", None, None),
    ("Precipitable water [kg/m2]", pw, "Greens", np.percentile(pw, 0.1), np.percentile(pw, 99.9)),
]
fig, axes = plt.subplots(3, 3, figsize=(10, 9.5), constrained_layout=True)
for r, (name, arr, cmap, vmin, vmax) in enumerate(rows):
    if vmin is None:                                         # 鉛直流は 0 を中心にそろえる
        vmax = max(0.5, np.percentile(np.abs(arr[its]), 99.9))
        vmin = -vmax
    for c, it in enumerate(its):
        ax = axes[r, c]
        im = ax.imshow(arr[it], origin="lower", extent=ext, cmap=cmap, vmin=vmin, vmax=vmax)
        ax.set_title(f"{name}\nt = {time_min[it]:.0f} min", color=ink)
        ax.set_aspect("equal")
        if r == 2:
            ax.set_xlabel("x [km]")
        if c == 0:
            ax.set_ylabel("y [km]")
    fig.colorbar(im, ax=axes[r, :], shrink=0.9)
fig.suptitle(f"Phase 3 single forecast, member {MEM} (2 km, 120 x 120, doubly periodic)", color=ink)
fig.savefig(f"{FIGDIR}/fcst1h_maps.png", dpi=110)
plt.close(fig)

# ---- 図 2: 時系列（変数ごとに別の軸） -----------------------------------------
series = [
    ("Domain-mean precipitation [mm/h]", prec.mean(axis=(1, 2))),
    ("Max precipitation [mm/h]", prec.max(axis=(1, 2))),
    ("Max updraft (any level) [m/s]", wmax_col.max(axis=(1, 2))),
    ("Max hydrometeor mixing ratio [g/kg]", qhyd_col.max(axis=(1, 2))),
    ("Domain-mean T2 [K]", t2.mean(axis=(1, 2))),
    ("Domain-mean OLR [W/m2]", olr.mean(axis=(1, 2))),
    ("Domain-mean precipitable water [kg/m2]", pw.mean(axis=(1, 2))),
    ("Domain-mean top-layer soil moisture [m3/m3]", lwat.mean(axis=(1, 2))),
]
fig, axes = plt.subplots(4, 2, figsize=(10, 9), sharex=True, constrained_layout=True)
for ax, (name, val) in zip(axes.flat, series):
    ax.plot(time_min, val, color="#2f6fb3", lw=2)
    ax.set_title(name, color=ink, loc="left")
    ax.grid(color="#d8dee4", lw=0.6)
    ax.spines[["top", "right"]].set_visible(False)
    ax.ticklabel_format(axis="y", useOffset=False)
for ax in axes[-1]:
    ax.set_xlabel("Time since 2000-01-01 00:00 [min]")
fig.suptitle(f"Phase 3 single forecast, member {MEM}: time series (1-min history)", color=ink)
fig.savefig(f"{FIGDIR}/fcst1h_timeseries.png", dpi=110)
plt.close(fig)

# ---- 図 3: 鉛直分布 -----------------------------------------------------------
zkm = z / 1e3
early, late = "#9ecae1", "#08519c"                          # 同じ色相の薄い・濃い
fig, axes = plt.subplots(1, 3, figsize=(10, 4.5), sharey=True, constrained_layout=True)
for ax, (name, prof) in zip(axes, [("Potential temperature [K]", pt_mean),
                                   ("Water vapor QV [g/kg]", qv_mean),
                                   ("Hydrometeors QHYD [g/kg]", qhyd_mean)]):
    ax.plot(prof[0], zkm, color=early, lw=2, label=f"t = {time_min[0]:.0f} min")
    ax.plot(prof[-1], zkm, color=late, lw=2, label=f"t = {time_min[-1]:.0f} min")
    ax.set_title(name, color=ink)
    ax.grid(color="#d8dee4", lw=0.6)
    ax.spines[["top", "right"]].set_visible(False)
axes[0].set_ylabel("Height [km]")
axes[0].set_ylim(0, 20)
axes[0].legend(frameon=False)
fig.suptitle(f"Phase 3 single forecast, member {MEM}: domain-mean profiles", color=ink)
fig.savefig(f"{FIGDIR}/fcst1h_profiles.png", dpi=110)
plt.close(fig)

# ---- 数値のまとめ --------------------------------------------------------------
print(f"W level: k={kw}, z={z[kw]:.0f} m")
for name, val in series:
    print(f"{name:45s} t=1: {val[0]:10.4g}  t=60: {val[-1]:10.4g}  max: {val.max():10.4g}")
print("figures:", os.path.abspath(FIGDIR))
