#!/usr/bin/env python3
"""制御の目標領域（x = 80 km・y = 120 km を中心とする 20 km 四方）の降水の時間変化（Phase 9、2026-11-02）。

目標領域: 格子番号 i = 35〜44・j = 55〜64（0 始まり。x 70〜90 km・y 110〜130 km）の 10 × 10 格子。
各 cycle の 1 時間予報の history（<OUTDIR>/<t>/hist/<mem>）の地上降水強度 PREC [kg/m²/s = mm/s] を、目標領域で平均する。
- 10 分ごと: 600〜3600 s の瞬間値を mm/h にしたもの（0 s は前の cycle の 3600 s と重なるので除く）
- 1 時間ごと: 600〜3600 s の 6 時刻 × 600 s の和（plot_member_prec.py と同じ近似）
定式化の Σ_{(x,y)∈D_i} P（格子の和）は、この平均 × 100。
読むのは目標領域を含む 4 プロセス分のファイルだけ（どのファイルかは mdet の最初の cycle の x, y で決める）。

使い方: cd analysis && STIME=20000131000000 OUTDIR=… FIGDIR=… python3 plot/plot_target_prec.py [cycle 数（既定 24）] [member 数（既定 80）]
出力: 表（標準出力）と FIGDIR/target_prec.png・target_prec.npz（2 回目からは npz を読んで図だけ描き直す。作り直すときは消す）
"""
import glob
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from netCDF4 import Dataset

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))   # analysis/common.py
import common as cm
from common import tstr

NCYC = int(sys.argv[1]) if len(sys.argv) > 1 else 24
NMEM = int(sys.argv[2]) if len(sys.argv) > 2 else 80
MEMS = [f"{m:04d}" for m in range(1, NMEM + 1)] + ["mdet"]
DT = 600.0                                          # history の間隔 [s]
I0, J0, K = 35, 55, 10                              # 目標領域の左下の格子番号（0 始まり）と一辺の格子数
NT = int(3600 / DT)                                 # 1 cycle の 10 分値の数（600〜3600 s）

cm.use_japanese_font()


def target_files():
    """目標領域を含むファイル名（history.peXXXXXX.nc）と、その中で目標領域に入る局所の格子番号。"""
    sel = []
    for f in sorted(glob.glob(f"{cm.hist_dir('mdet', tstr(0))}/history.pe*.nc")):
        with Dataset(f) as d:
            i, j = cm._ij(d)
        ii = np.flatnonzero((i >= I0) & (i < I0 + K))
        jj = np.flatnonzero((j >= J0) & (j < J0 + K))
        if ii.size and jj.size:
            sel.append((os.path.basename(f), ii, jj))
    if sum(len(ii) * len(jj) for _, ii, jj in sel) != K * K:
        sys.exit(f"目標領域の {K * K} 格子がファイルから埋まりません: {sel}")
    return sel


def series(args):
    """mem の目標領域の平均降水強度 [mm/h] を、10 分ごとに NCYC × NT 個。"""
    mem, sel = args
    out = np.full(NCYC * NT, np.nan)
    for k in range(NCYC):
        d0 = cm.hist_dir(mem, tstr(k))
        s = np.zeros(NT + 1)
        for name, ii, jj in sel:
            with Dataset(f"{d0}/{name}") as d:
                tt = np.asarray(d.variables["time"][:])
                if not np.allclose(tt, np.arange(0, 3601, DT)):
                    sys.exit(f"{mem} の {tstr(k)} の history の時刻が足りない（time = {tt}）")
                s += np.asarray(d.variables["PREC"][:, jj[0]:jj[-1] + 1, ii[0]:ii[-1] + 1], dtype=np.float64).sum(axis=(1, 2))
        out[k * NT:(k + 1) * NT] = s[1:] / (K * K) * 3600.0
    return mem, out


def main():
    out = cm.figdir()
    cache = f"{out}/target_prec.npz"
    if os.path.exists(cache):
        r = dict(np.load(cache))
    else:
        sel = target_files()
        print("目標領域を含むファイル: " + "、".join(f"{n}（局所 i {ii[0]}〜{ii[-1]}・j {jj[0]}〜{jj[-1]}）" for n, ii, jj in sel))
        with ProcessPoolExecutor(max_workers=8) as ex:
            r = dict(ex.map(series, [(m, sel) for m in MEMS]))
        np.savez_compressed(cache, **r)
    ens = np.array([r[m] for m in MEMS[:-1]])       # (member, 時刻) 10 分ごと [mm/h]
    md = r["mdet"]
    t10 = (np.arange(NCYC * NT) + 1) * DT / 3600.0  # 時刻 [h]（STIME から）
    hr_e = ens.reshape(len(ens), NCYC, NT).mean(axis=2)   # 1 時間降水量 [mm]（= 1 時間の平均強度 [mm/h]）
    hr_m = md.reshape(NCYC, NT).mean(axis=1)
    th = np.arange(NCYC) + 0.5                      # 1 時間の値は区間の真ん中に描く

    print(f"目標領域: x {I0 * 2}〜{(I0 + K) * 2} km・y {J0 * 2}〜{(J0 + K) * 2} km（{K} × {K} 格子）の平均。"
          f"1 時間降水量 [mm]（格子の和は × {K * K}）")
    print(" 時間     mdet   平均   p10    p50    p90    最大   mdet の順位（多い順 / {}）".format(len(ens)))
    for k in range(NCYC):
        e = hr_e[:, k]
        rank = int((e > hr_m[k]).sum()) + 1
        print(f" {k:2d}-{k + 1:2d}  {hr_m[k]:6.2f} {e.mean():6.2f} {np.percentile(e, 10):6.2f} {np.percentile(e, 50):6.2f} "
              f"{np.percentile(e, 90):6.2f} {e.max():6.2f}   {rank:2d}")
    print(f"24 時間の合計 [mm]: mdet {hr_m.sum():.2f}、member 平均 {hr_e.sum(axis=1).mean():.2f}"
          f"（最小 {hr_e.sum(axis=1).min():.2f}・最大 {hr_e.sum(axis=1).max():.2f}）")

    fig, axs = plt.subplots(2, 1, figsize=(11, 7.6), sharex=True, constrained_layout=True)
    for ax, x, e, m, unit, ttl in [
            (axs[0], th, hr_e, hr_m, "1 時間降水量 [mm]", "(a) 1 時間ごと"),
            (axs[1], t10, ens, md, "降水強度 [mm/h]", "(b) 10 分ごと（瞬間値）")]:
        ax.axvspan(0, 7, color="0.92", zorder=0, lw=0)
        for row in e:
            ax.plot(x, row, color=cm.GRAY, lw=0.4, alpha=0.35)
        ax.fill_between(x, np.percentile(e, 10, axis=0), np.percentile(e, 90, axis=0), color=cm.C1, alpha=0.25, lw=0,
                        label="member の 10〜90%")
        ax.plot(x, e.mean(axis=0), color=cm.C1, lw=1.8, label=f"member 平均（{len(e)}）")
        ax.plot(x, m, color="k", lw=1.8, label="mdet（現実の側）")
        ax.set_ylabel(unit)
        ax.set_title(ttl, loc="left", fontsize=11)
        ax.grid(alpha=0.3)
        ax.set_ylim(bottom=0)
    axs[0].text(3.5, axs[0].get_ylim()[1] * 0.95, "同化の誤差が\n横ばいになる前", ha="center", va="top", fontsize=9, color="0.4")
    axs[0].legend(frameon=False, loc="upper right", fontsize=9)
    axs[1].set_xlabel("STIME からの時間 [h]")
    axs[1].set_xlim(0, NCYC)
    axs[1].set_xticks(np.arange(0, NCYC + 1, 2))
    fig.suptitle(f"制御の目標領域（x {I0 * 2}〜{(I0 + K) * 2} km・y {J0 * 2}〜{(J0 + K) * 2} km、20 km 四方）の平均降水",
                 fontsize=12, x=0.01, ha="left")
    fig.savefig(f"{out}/target_prec.png", dpi=110)
    print(f"図: {out}/target_prec.png")


if __name__ == "__main__":
    main()
