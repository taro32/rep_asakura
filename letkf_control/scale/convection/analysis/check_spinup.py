#!/usr/bin/env python3
"""Phase 7d: 30 日スピンアップで平衡に近づいたかを、history（1 時間ごと）の領域平均の時間変化で調べる。

- 領域平均: 降水（PREC）、潜熱・顕熱フラックス（LHFLX, SHFLX）、OLR、可降水量（PW）、2 m 気温（T2）、
  土壌水分（LAND_WATER の各層）。土壌水分は最上層の水平方向の標準偏差・最小・最大も出す。
- 最後の 5 日（25〜30 日）と、その前の 5 日（20〜25 日）の平均を比べる。
- 20000131 の restart の土壌水分（全層）の分布。

出力: 表（標準出力）と FIGDIR/spinup_timeseries.png
使い方: FIGDIR=… python3 check_spinup.py
"""
import glob
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from netCDF4 import Dataset

import common as cm

O = "/work/gv42/v42013/20260923_enkc_convection/spinup_20261003"
V2 = ["PREC", "LHFLX", "SHFLX", "OLR", "PW", "T2"]


def main():
    labels = sorted({os.path.basename(f).split(".pe")[0] for f in glob.glob(f"{O}/history/history_*.pe000000.nc")})
    t_all, s2, w_mean, w_std, w_min, w_max = [], {v: [] for v in V2}, [], [], [], []
    for lab in labels:
        files = sorted(glob.glob(f"{O}/history/{lab}.pe*.nc"))
        acc = None
        for f in files:
            with Dataset(f) as d:
                t = np.asarray(d.variables["time"][:])
                cur = {v: np.asarray(d.variables[v][:], dtype=np.float64).sum(axis=(1, 2)) for v in V2}
                lw = np.asarray(d.variables["LAND_WATER"][:], dtype=np.float64)          # (t, lz, y, x)
                cur["W"] = lw.sum(axis=(2, 3))
                cur["W2"] = (lw[:, 0] ** 2).sum(axis=(1, 2))
                cur["Wmin"] = lw[:, 0].min(axis=(1, 2))
                cur["Wmax"] = lw[:, 0].max(axis=(1, 2))
                cur["n"] = lw.shape[2] * lw.shape[3]
            if acc is None:
                acc = cur
            else:
                for k in cur:
                    if k == "Wmin":
                        acc[k] = np.minimum(acc[k], cur[k])
                    elif k == "Wmax":
                        acc[k] = np.maximum(acc[k], cur[k])
                    else:
                        acc[k] = acc[k] + cur[k]
        n = acc["n"]
        t_all.append(t)
        for v in V2:
            s2[v].append(acc[v] / n)
        wm = acc["W"] / n
        w_mean.append(wm)
        w_std.append(np.sqrt(np.maximum(acc["W2"] / n - wm[:, 0] ** 2, 0)))
        w_min.append(acc["Wmin"])
        w_max.append(acc["Wmax"])
    t = np.concatenate(t_all) / 86400.0
    order = np.argsort(t)
    t = t[order]
    s2 = {v: np.concatenate(s2[v])[order] for v in V2}
    s2["PREC"] = s2["PREC"] * 3600.0                     # kg/m2/s -> mm/h
    wm = np.concatenate(w_mean)[order]
    ws = np.concatenate(w_std)[order]
    wmin = np.concatenate(w_min)[order]
    wmax = np.concatenate(w_max)[order]

    def avg(x, a, b):
        sel = (t >= a) & (t < b)
        return x[sel].mean(axis=0)

    print(f"history: {len(t)} 時刻（{t[0]:.2f}〜{t[-1]:.2f} 日）")
    print(f"{'量':22s} {'0〜1 日':>10s} {'20〜25 日':>10s} {'25〜30 日':>10s}  変化(25-30 / 20-25 − 1)")
    units = {"PREC": "mm/h", "LHFLX": "W/m2", "SHFLX": "W/m2", "OLR": "W/m2", "PW": "kg/m2", "T2": "K"}
    for v in V2:
        a0, a1, a2 = avg(s2[v], 0, 1), avg(s2[v], 20, 25), avg(s2[v], 25, 30.01)
        print(f"{v + ' [' + units[v] + ']':22s} {a0:10.4f} {a1:10.4f} {a2:10.4f}  {a2 / a1 - 1:+.3f}")
    for k in range(wm.shape[1]):
        a0, a1, a2 = avg(wm[:, k], 0, 1), avg(wm[:, k], 20, 25), avg(wm[:, k], 25, 30.01)
        print(f"{'LAND_WATER 層' + str(k + 1):22s} {a0:10.4f} {a1:10.4f} {a2:10.4f}  {a2 / a1 - 1:+.3f}")
    print(f"最上層の土壌水分（30 日目の最後）: 平均 {wm[-1, 0]:.4f}、水平の標準偏差 {ws[-1]:.4f}、最小 {wmin[-1]:.4f}、最大 {wmax[-1]:.4f}")

    # 20000131 の restart の土壌水分
    vals = []
    for f in sorted(glob.glob(f"{O}/restart/restart_20000131-000000.000.pe*.nc")):
        with Dataset(f) as d:
            vals.append(np.asarray(d.variables["LAND_WATER"][:]).reshape(-1, 7))
    vals = np.concatenate(vals)
    print("restart_20000131 の LAND_WATER（層ごと）:")
    for k in range(7):
        x = vals[:, k]
        print(f"  層 {k + 1}: 平均 {x.mean():.4f} 標準偏差 {x.std():.4f} 最小 {x.min():.4f} 最大 {x.max():.4f}")

    # 図
    out = cm.figdir()
    fig, axs = plt.subplots(2, 4, figsize=(18, 7.5), sharex=True)
    for ax, v in zip(axs.ravel(), V2):
        ax.plot(t, s2[v], lw=0.6, color="#9aa5b1")
        k = 24
        if len(t) > k:
            ax.plot(t[k - 1:], np.convolve(s2[v], np.ones(k) / k, mode="valid"), color="#1c2733", lw=1.5, label="24 h mean")
        ax.set_title(f"{v} [{units[v]}]")
        ax.grid(alpha=0.3)
    ax = axs.ravel()[6]
    for k in range(wm.shape[1]):
        ax.plot(t, wm[:, k], lw=1.2, label=f"layer {k + 1}")
    ax.set_title("LAND_WATER domain mean [m3/m3]")
    ax.legend(fontsize=8, ncol=2)
    ax.grid(alpha=0.3)
    ax = axs.ravel()[7]
    ax.plot(t, ws, color="#c2410c", label="std (top layer)")
    ax.set_title("LAND_WATER top layer: horizontal std")
    ax.grid(alpha=0.3)
    for a in axs[1]:
        a.set_xlabel("day")
    axs[0, 0].legend(fontsize=8)
    fig.suptitle("30-day spin-up: domain-mean time series (hourly)")
    fig.tight_layout()
    fig.savefig(f"{out}/spinup_timeseries.png", dpi=110)
    print(f"図: {out}/spinup_timeseries.png")


if __name__ == "__main__":
    main()
