#!/usr/bin/env python3
"""パッチ型の摂動の予報で、格子ごとのボーエン比の相関の地図を 2 枚描く（2026-11-04）。

phase9_patch_t08（8 時に 20 km 四方のパッチごとの土壌水分の摂動を入れ、18 時まで予報した 80 member）を使う。標本は 80 member。
- 地図 1: 格子ごとの、土壌水分の摂動 u（第 1 層、perturbation.npz）と、その格子のボーエン比 B の相関
- 地図 2: 格子ごとの B と、目標領域の雨 Y（13〜17 時の合計、check_patch_fcst.py の patch_fcst.npz から）の相関
B は HOUR 時〜HOUR + 1 時の 1 時間平均の顕熱 / 潜熱（格子ごと）。80 member で偶然と区別できるのは |r| > 0.22（両側 5%）。

使い方: cd analysis && FIGDIR=… [HOUR=10] python3 control/20261103_patch_fcst/check_patch_bowen_map.py [実験の場所（既定 …/phase9_patch_t08）]
出力: 表（標準出力）と FIGDIR/patch_bowen_map_<HOUR>.png・patch_bowen_map_<HOUR>.npz
     （2 回目からは npz を読んで図だけ描き直す。作り直すときは消す）
"""
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle
from netCDF4 import Dataset

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))   # analysis/common.py
import common as cm
from common import DX, NX, NY

EXP = sys.argv[1] if len(sys.argv) > 1 else "/work/gv42/v42013/20260923_enkc_convection/phase9_patch_t08"
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE_Y = f"{HERE}/../../../docs/control/20261103_patch_fcst/patch_fcst.npz"   # 目標領域の時系列（check_patch_fcst.py）
T0 = 8
HOUR = int(os.environ.get("HOUR", 10))
I0, J0, K = 35, 55, 10
RC = 0.22

cm.use_japanese_font()


def bowen(mem):
    """mem の格子ごとのボーエン比（HOUR 時〜HOUR + 1 時の 1 時間平均の顕熱 / 潜熱）。"""
    k0 = 1 + 6 * (HOUR - T0)                         # 10 分ごとの出力の番号（0 = 8 時）。k0〜k0 + 5 が 1 時間分
    sh = np.full((NY, NX), np.nan)
    lh = np.full((NY, NX), np.nan)
    for f in sorted(os.listdir(f"{EXP}/hist/{mem}")):
        with Dataset(f"{EXP}/hist/{mem}/{f}") as d:
            i, j = cm._ij(d)
            sh[np.ix_(j, i)] = np.asarray(d.variables["SHFLX"][k0:k0 + 6], dtype=np.float64).mean(axis=0)
            lh[np.ix_(j, i)] = np.asarray(d.variables["LHFLX"][k0:k0 + 6], dtype=np.float64).mean(axis=0)
    if np.isnan(sh).any():
        sys.exit(f"{mem}: 埋まっていない格子があります。")
    return mem, sh / lh


def corr(a, y):
    """a（member, ...）と y（member, ... または member）の、格子ごとの相関。"""
    if y.ndim == 1:
        y = y.reshape(-1, *([1] * (a.ndim - 1)))
    aa = a - a.mean(axis=0)
    ya = y - y.mean(axis=0)
    return (aa * ya).sum(axis=0) / np.sqrt((aa ** 2).sum(axis=0) * (ya ** 2).sum(axis=0))


def main():
    out = cm.figdir()
    cache = f"{out}/patch_bowen_map_{HOUR}.npz"
    pz = np.load(f"{EXP}/perturbation.npz")
    nmem = int(str(pz["mdet"])) - 1
    mems = [f"{k:04d}" for k in range(1, nmem + 1)]
    if os.path.exists(cache):
        B = np.load(cache)["B"]
    else:
        with ProcessPoolExecutor(max_workers=8) as ex:
            r = dict(ex.map(bowen, mems))
        B = np.array([r[m] for m in mems])
        np.savez_compressed(cache, B=B, hour=HOUR)
    U = np.array([pz[m] for m in mems])
    c = np.load(CACHE_Y)
    P = np.array([c[f"{m}_PREC"] for m in mems])
    hr = P[:, 1:].reshape(nmem, -1, 6).mean(axis=2)
    Y = hr[:, 13 - T0:17 - T0].sum(axis=1)

    r1 = corr(U, B)
    r2 = corr(B, Y)
    tgt = (slice(J0, J0 + K), slice(I0, I0 + K))
    print(f"実験: {EXP}（member {nmem}）。ボーエン比は {HOUR}〜{HOUR + 1} 時の 1 時間平均")
    print(f"地図 1（土壌水分の摂動とボーエン比）: 領域の中央値 {np.median(r1):+.3f}、10% 点 {np.percentile(r1, 10):+.3f}、"
          f"90% 点 {np.percentile(r1, 90):+.3f}。目標領域の平均 {r1[tgt].mean():+.3f}")
    print(f"   r² の領域の中央値 {np.median(r1 ** 2):.3f}（ボーエン比の member 間のばらつきのうち、その格子の摂動で説明できる割合）")
    print(f"地図 2（ボーエン比と目標領域の雨 Y）: |r| > {RC} の格子の割合 {(np.abs(r2) > RC).mean() * 100:.1f}%"
          f"（偶然でも約 5%）。目標領域の平均 {r2[tgt].mean():+.3f}、最大 {r2.max():+.3f}、最小 {r2.min():+.3f}")
    Bt = B[:, tgt[0], tgt[1]].mean(axis=(1, 2))
    print(f"   目標領域で平均したボーエン比と Y の相関 {np.corrcoef(Bt, Y)[0, 1]:+.3f}")

    ext = [0, NX * DX / 1e3, 0, NY * DX / 1e3]
    fig, axs = plt.subplots(1, 2, figsize=(13, 5.6), constrained_layout=True)
    for ax, rr, ttl in [(axs[0], r1, f"(a) 土壌水分の摂動とボーエン比（{HOUR}〜{HOUR + 1} 時）"),
                        (axs[1], r2, f"(b) ボーエン比（{HOUR}〜{HOUR + 1} 時）と目標領域の雨（13〜17 時の合計）")]:
        im = ax.imshow(rr, origin="lower", extent=ext, cmap="RdBu_r", vmin=-1, vmax=1)
        ax.contour(np.abs(rr) > RC, levels=[0.5], origin="lower", extent=ext, colors="0.3", linewidths=0.4)
        ax.add_patch(Rectangle((I0 * DX / 1e3, J0 * DX / 1e3), K * DX / 1e3, K * DX / 1e3, fill=False, ec="k", lw=1.5))
        ax.set_title(ttl, loc="left", fontsize=10)
        ax.set_xlabel("x [km]")
    axs[0].set_ylabel("y [km]")
    fig.colorbar(im, ax=axs, shrink=0.85, label="80 member の相関 r")
    fig.suptitle(f"格子ごとの相関（パッチ型の摂動の予報、80 member）。黒枠 = 目標領域、灰色の線 = |r| = {RC}（両側 5%）",
                 fontsize=11, x=0.01, ha="left")
    fig.savefig(f"{out}/patch_bowen_map_{HOUR}.png", dpi=110)
    print(f"図: {out}/patch_bowen_map_{HOUR}.png")


if __name__ == "__main__":
    main()
