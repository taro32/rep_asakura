#!/usr/bin/env python3
"""持ち上げ凝結高度（LCL）と、境界層の高さとの差（LCL の不足分）を、パッチ型の摂動の予報で見る（2026-11-03）。

対流が始まる条件 ≒ 境界層の上端が LCL に届くこと。LCL の不足分 D = LCL − 境界層の高さ で測ると、
正のフィードバック（湿らせると LCL が下がる）と負のフィードバック（乾かすと境界層が厚くなる）の両方が、D の上で綱引きをする。
- LCL: 地上 2 m の気温 T2・比湿 Q2・地上気圧 SFC_PRES から格子ごとに計算する。露点は Bolton (1980)、
  凝結する温度 T_LCL は Bolton (1980) の式 (15)、高さは乾燥断熱で (T2 − T_LCL) / (g/cp)
- D = LCL − PBLH（格子ごと）。目標領域で平均した D と、D ≤ 0（境界層が LCL に届いた）格子の割合
- 雨の降り始め: 目標領域の平均降水強度（10 分ごと）が ONSET [mm/h] を初めて超えた時刻
- 見る相関: 目標のパッチの摂動 u と、各量（1 時間平均）/ 降り始めの時刻 / 各量（1 時間平均）と降り始めの時刻

使い方: cd analysis && FIGDIR=… python3 control/20261103_patch_fcst/check_patch_lcl.py [実験の場所（既定 …/phase9_patch_t08）]
出力: 表（標準出力）と FIGDIR/patch_lcl.png・patch_lcl.npz（2 回目からは npz を読んで図だけ描き直す。作り直すときは消す）
"""
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from netCDF4 import Dataset

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))   # analysis/common.py
import common as cm
from common import NX, NY

EXP = sys.argv[1] if len(sys.argv) > 1 else "/work/gv42/v42013/20260923_enkc_convection/phase9_patch_t08"
T0 = 8
I0, J0, K = 35, 55, 10
DT = 600.0
ONSET = 1.0                                         # 降り始めの基準 [mm/h]（目標領域の平均）
G_CP = 9.81 / 1004.0                                # 乾燥断熱減率 [K/m]
QTY = ["LCL", "PBLH", "DEF", "TRIG", "T2", "Q2", "PREC"]
LABEL = {"LCL": "LCL [m]", "PBLH": "境界層の高さ [m]", "DEF": "LCL の不足分 D = LCL − 境界層の高さ [m]",
         "TRIG": "境界層が LCL に届いた格子の割合", "T2": "2 m 気温 [K]", "Q2": "2 m 比湿 [g/kg]", "PREC": "降水強度 [mm/h]"}

cm.use_japanese_font()


def lcl(t2, q2, ps):
    """格子ごとの LCL の高さ [m]（地上から）。t2 [K]、q2 [kg/kg]、ps [Pa]。"""
    e = q2 * ps / (0.622 + 0.378 * q2) / 100.0                  # 水蒸気圧 [hPa]
    x = np.log(np.maximum(e, 1e-6) / 6.112)
    td = 243.5 * x / (17.67 - x) + 273.15                        # 露点 [K]（Bolton 1980）
    tl = 1.0 / (1.0 / (td - 56.0) + np.log(t2 / td) / 800.0) + 56.0   # 凝結する温度 [K]（Bolton 1980、式 15）
    return (t2 - tl) / G_CP


def series(mem):
    """mem の目標領域の各量（10 分ごと）。"""
    acc = {q: 0.0 for q in QTY}
    n = 0
    for f in sorted(os.listdir(f"{EXP}/hist/{mem}")):
        with Dataset(f"{EXP}/hist/{mem}/{f}") as d:
            i, j = cm._ij(d)
            ii = np.flatnonzero((i >= I0) & (i < I0 + K))
            jj = np.flatnonzero((j >= J0) & (j < J0 + K))
            if not (ii.size and jj.size):
                continue
            sl = (slice(None), slice(jj[0], jj[-1] + 1), slice(ii[0], ii[-1] + 1))
            a = {v: np.asarray(d.variables[v][sl], dtype=np.float64) for v in ["T2", "Q2", "SFC_PRES", "PBLH", "PREC"]}
        z = lcl(a["T2"], a["Q2"], a["SFC_PRES"])
        dd = z - a["PBLH"]
        vals = {"LCL": z, "PBLH": a["PBLH"], "DEF": dd, "TRIG": (dd <= 0).astype(float), "T2": a["T2"],
                "Q2": a["Q2"] * 1000.0, "PREC": a["PREC"] * 3600.0}
        for q in QTY:
            acc[q] = acc[q] + vals[q].sum(axis=(1, 2))
        n += ii.size * jj.size
    if n != K * K:
        sys.exit(f"{mem}: 目標領域の格子が {n} 個です。")
    return mem, {q: acc[q] / n for q in QTY}


def main():
    out = cm.figdir()
    cache = f"{out}/patch_lcl.npz"
    pz = np.load(f"{EXP}/perturbation.npz")
    det = str(pz["mdet"])
    mems = [f"{k:04d}" for k in range(1, int(det))]
    if os.path.exists(cache):
        z = dict(np.load(cache))
        r = {m: {q: z[f"{m}_{q}"] for q in QTY} for m in mems + [det]}
    else:
        with ProcessPoolExecutor(max_workers=8) as ex:
            r = dict(ex.map(series, mems + [det]))
        np.savez_compressed(cache, **{f"{m}_{q}": r[m][q] for m in r for q in QTY})

    nt = len(r[det]["PREC"])
    t = T0 + np.arange(nt) * DT / 3600.0
    E = {q: np.array([r[m][q] for m in mems]) for q in QTY}
    off, P = int(pz["offset"]), int(pz["patch"])
    u = np.array([np.roll(np.roll(pz[m], -off, 0), -off, 1)[J0 - off:J0 - off + P, I0 - off:I0 - off + P].mean() for m in mems])

    def onset(p):
        k = np.flatnonzero(p > ONSET)
        return t[k[0]] if k.size else np.nan
    ton = np.array([onset(p) for p in E["PREC"]])
    ton_md = onset(r[det]["PREC"])
    ok = np.isfinite(ton)
    print(f"実験: {EXP}（member {len(mems)}）。目標のパッチの摂動 u の標準偏差 {u.std():.4f}")
    print(f"雨の降り始め（目標領域の平均が {ONSET} mm/h を超えた時刻）: member の平均 {np.nanmean(ton):.2f} 時、"
          f"標準偏差 {np.nanstd(ton):.2f} 時間、範囲 {np.nanmin(ton):.2f}〜{np.nanmax(ton):.2f} 時、"
          f"降らなかった member {(~ok).sum()}、mdet {ton_md:.2f} 時")
    print(f"u と降り始めの時刻の相関: r = {np.corrcoef(u[ok], ton[ok])[0, 1]:+.2f}"
          f"（傾き {np.polyfit(u[ok], ton[ok], 1)[0] * 0.01 * 60:+.1f} 分 / 0.01 m³/m³）")

    hv = {q: E[q][:, 1:].reshape(len(mems), -1, 6).mean(axis=2) for q in QTY}   # 1 時間平均（列 h = T0 + h 時〜）
    print("\n1 時間平均の各量: member 平均（標準偏差）/ u との相関 / 降り始めの時刻との相関")
    for q in ["LCL", "PBLH", "DEF", "TRIG", "T2", "Q2"]:
        print(f" {LABEL[q]}")
        for h in range(0, 7):                          # 8〜15 時
            a = hv[q][:, h]
            ru = np.corrcoef(u, a)[0, 1]
            rt = np.corrcoef(a[ok], ton[ok])[0, 1]
            print(f"   {T0 + h:2d}〜{T0 + h + 1:2d} 時: {a.mean():9.3f}（{a.std():7.3f}）  u との r {ru:+.2f}  降り始めとの r {rt:+.2f}")

    # ---- 図
    panels = ["PREC", "PBLH", "LCL", "DEF", "TRIG"]
    fig, axs = plt.subplots(len(panels) + 1, 1, figsize=(11, 15), constrained_layout=True)
    wet = u > np.median(u)
    for ax, q in zip(axs, panels):
        ax.axvspan(13, 17, color=cm.C3, alpha=0.08, lw=0)
        for row, w in zip(E[q], wet):
            ax.plot(t, row, color=cm.C1 if w else cm.C2, lw=0.4, alpha=0.35)
        ax.plot(t, E[q][wet].mean(axis=0), color=cm.C1, lw=1.8, label="目標のパッチを湿らせた半分の平均")
        ax.plot(t, E[q][~wet].mean(axis=0), color=cm.C2, lw=1.8, label="目標のパッチを乾かした半分の平均")
        ax.plot(t, r[det][q], color="k", lw=1.4, label="mdet")
        if q == "DEF":
            ax.axhline(0, color="0.4", lw=1)
        ax.set_ylabel(LABEL[q], fontsize=9)
        ax.set_xlim(T0, t[-1])
        ax.grid(alpha=0.3)
    axs[0].legend(frameon=False, fontsize=8, ncol=3, loc="upper left")
    axs[len(panels) - 1].set_xlabel("STIME からの時間 [h]")
    ax = axs[-1]
    ax.scatter(u[ok] * 100, ton[ok], s=14, color=cm.C1)
    c = np.polyfit(u[ok], ton[ok], 1)
    xx = np.linspace(u.min(), u.max(), 2)
    ax.plot(xx * 100, np.polyval(c, xx), color="0.4", lw=1)
    ax.set_xlabel("目標のパッチの摂動 [10⁻² m³/m³]")
    ax.set_ylabel(f"雨の降り始め [時]\n（> {ONSET} mm/h）", fontsize=9)
    ax.set_title(f"摂動と降り始めの時刻: r = {np.corrcoef(u[ok], ton[ok])[0, 1]:+.2f}", loc="left", fontsize=10)
    ax.grid(alpha=0.3)
    fig.suptitle("目標領域の LCL・境界層の高さ・LCL の不足分（80 member を、目標のパッチの摂動の正負で色分け）", fontsize=12, x=0.01, ha="left")
    fig.savefig(f"{out}/patch_lcl.png", dpi=110)
    print(f"\n図: {out}/patch_lcl.png")


if __name__ == "__main__":
    main()
