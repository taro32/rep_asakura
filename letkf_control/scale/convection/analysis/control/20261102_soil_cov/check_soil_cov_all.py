#!/usr/bin/env python3
"""土壌水分と目標領域の雨の相関を、介入が考えられるすべての時刻（0〜12 時）で見る（2026-11-03）。

check_soil_cov.py（7〜12 時、第 1 層）を、0〜12 時と 3 つの土壌水分に広げたもの。
早い時刻ほど土壌水分のばらつきは大きい（0 時 0.0057）が、目標の雨（13〜17 時）までは遠い。どちらが効くかを見る。
- u: 時刻 t の解析の restart（<OUTDIR>/<t>/anal/<mem>。0 時は初期値）の LAND_WATER
    L1: 第 1 層（0〜5 cm）、L2: 第 2 層（5〜20 cm）、S20: 0〜20 cm の平均（厚さで重み付け）
- Y: 目標領域の平均降水（plot_target_prec.py の npz）。total: 13〜17 時の合計、peak: 15〜16 時の 1 時間降水量
- 有意な相関の格子の割合を、Y を並べ替えた 500 回（偶然だけの場合）の 95% 点と比べる。80 member の両側 5% は |r| > 0.22

使い方: cd analysis && STIME=20000131000000 OUTDIR=… FIGDIR=… python3 control/20261102_soil_cov/check_soil_cov_all.py [member 数（既定 80）]
出力: 表（標準出力）と FIGDIR/soil_cov_all_summary.png・soil_corr_all_S20.png・soil_cov_all.npz
     （2 回目からは npz を読んで図だけ描き直す。作り直すときは消す）
"""
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))   # analysis/common.py
import common as cm
from common import DX, NX, NY, tstr
from check_soil_cov import I0, J0, K, NPERM, RC, YNPZ, box, corr

NMEM = int(sys.argv[1]) if len(sys.argv) > 1 else 80
MEMS = [f"{m:04d}" for m in range(1, NMEM + 1)]
TINT = list(range(0, 13))                           # 介入が考えられる時刻 [h]（STIME から。雨は 13 時から）
DZ = np.array([0.05, 0.15])                         # 第 1・2 層の厚さ [m]
VARS = ["L1", "L2", "S20"]
LABEL = {"L1": "第 1 層（0〜5 cm）", "L2": "第 2 層（5〜20 cm）", "S20": "0〜20 cm の平均"}

cm.use_japanese_font()


def read_member(mem):
    """mem の時刻ごとの土壌水分（len(TINT), len(VARS), NY, NX）。"""
    out = np.full((len(TINT), len(VARS), NY, NX), np.nan, dtype=np.float32)
    for n, k in enumerate(TINT):
        t = tstr(k)
        w = cm.read_restart(cm.restart_dir("anal", mem, t), t=t, names=["LAND_WATER"])["LAND_WATER"]   # (層, NY, NX)
        out[n, 0] = w[0]
        out[n, 1] = w[1]
        out[n, 2] = (w[0] * DZ[0] + w[1] * DZ[1]) / DZ.sum()
    return out


def main():
    out = cm.figdir()
    cache = f"{out}/soil_cov_all.npz"
    if os.path.exists(cache):
        U = np.load(cache)["U"]
    else:
        with ProcessPoolExecutor(max_workers=8) as ex:
            U = np.array(list(ex.map(read_member, MEMS)))     # (member, 時刻, 変数, NY, NX)
        np.savez_compressed(cache, U=U)
    if np.isnan(U).any():
        sys.exit("LAND_WATER に埋まらない格子点があります。")

    z = np.load(YNPZ)
    hr = np.array([z[m] for m in MEMS]).reshape(len(MEMS), -1, 6).mean(axis=2)   # 1 時間降水量 [mm]
    Ys = {"total": (hr[:, 13:17].sum(axis=1), "13〜17 時の合計"), "peak": (hr[:, 15], "15〜16 時の 1 時間降水量")}

    np.seterr(invalid="ignore", divide="ignore")      # 0 時の第 2 層はばらつきが 0（相関は nan）
    rng = np.random.default_rng(0)
    res = {}                                          # (変数, Y) → 時刻ごとの (σ 中央値, σ 目標, 有意の割合, 並べ替え 95%, 目標領域の r)
    maps = {}
    for v_i, v in enumerate(VARS):
        for key, (y, lab) in Ys.items():
            rows = []
            for n, k in enumerate(TINT):
                u = U[:, n, v_i]
                sd = u.std(axis=0)
                r = corr(u, y)
                frac = (np.abs(r) > RC).mean()
                perm = np.array([(np.abs(corr(u, rng.permutation(y))) > RC).mean() for _ in range(NPERM)])
                ub = u[:, J0:J0 + K, I0:I0 + K].mean(axis=(1, 2))
                rows.append((np.median(sd), sd[J0:J0 + K, I0:I0 + K].mean(), frac, np.percentile(perm, 95),
                             np.corrcoef(ub, y)[0, 1]))
                if v == "S20" and key == "total":
                    maps[k] = (r, frac, np.percentile(perm, 95))
            res[(v, key)] = np.array(rows)

    for key, (y, lab) in Ys.items():
        print(f"\nY = 目標領域の平均降水（{lab}）: 平均 {y.mean():.2f} mm、標準偏差 {y.std():.2f} mm")
        for v in VARS:
            print(f"  u = {LABEL[v]}")
            print("   時刻  σ_u 領域の中央値  σ_u 目標領域  有意な格子の割合  偶然の 95% 点  目標領域の平均の u と Y の r")
            for k, row in zip(TINT, res[(v, key)]):
                print(f"   {k:2d} 時   {row[0]:.4f}          {row[1]:.4f}       {row[2] * 100:5.1f}%          "
                      f"{row[3] * 100:5.1f}%         {row[4]:+.2f}")

    # ---- 図 1: まとめ（時刻ごと）
    fig, axs = plt.subplots(1, 3, figsize=(15, 4.6), constrained_layout=True)
    cols = {"L1": cm.C1, "L2": cm.C2, "S20": "k"}
    for v in VARS:
        a = res[(v, "total")]
        axs[0].plot(TINT, a[:, 0], color=cols[v], marker="o", ms=3, label=f"{LABEL[v]}（領域の中央値）")
        axs[0].plot(TINT, a[:, 1], color=cols[v], marker="s", ms=3, ls="--", label=f"{LABEL[v]}（目標領域）")
        axs[1].plot(TINT, a[:, 2] * 100, color=cols[v], marker="o", ms=3, label=LABEL[v])
        axs[2].plot(TINT, a[:, 4], color=cols[v], marker="o", ms=3, label=f"{LABEL[v]}・13〜17 時の合計")
        axs[2].plot(TINT, res[(v, "peak")][:, 4], color=cols[v], marker="x", ms=4, ls=":", label=f"{LABEL[v]}・15〜16 時")
    perm95 = res[("S20", "total")][:, 3] * 100
    axs[1].fill_between(TINT, 0, perm95, color="0.85", lw=0, label="偶然の範囲（並べ替えの 95% 点まで）")
    axs[2].axhspan(-RC, RC, color="0.88", lw=0, label=f"偶然の範囲（|r| < {RC}）")
    axs[0].set_yscale("log")
    axs[0].set_ylabel("member 間の標準偏差 [m³/m³]")
    axs[0].set_title("(a) 土壌水分のばらつき", loc="left", fontsize=11)
    axs[1].set_ylabel("|r| > 0.22 の格子の割合 [%]")
    axs[1].set_title("(b) 有意な相関の格子の割合（Y = 13〜17 時の合計）", loc="left", fontsize=11)
    axs[2].set_ylabel("相関 r")
    axs[2].set_title("(c) 目標領域の平均の土壌水分と Y の相関", loc="left", fontsize=11)
    for ax in axs:
        ax.set_xlabel("介入の時刻 t [h]（STIME から）")
        ax.set_xticks(TINT)
        ax.grid(alpha=0.3, which="both")
        ax.legend(frameon=False, fontsize=7)
    fig.suptitle(f"土壌水分（時刻 t）と目標領域の雨の相関（{len(MEMS)} member）", fontsize=12, x=0.01, ha="left")
    fig.savefig(f"{out}/soil_cov_all_summary.png", dpi=110)

    # ---- 図 2: 相関の地図（0〜20 cm の平均、13〜17 時の合計）
    ext = [0, NX * DX / 1e3, 0, NY * DX / 1e3]
    fig, axs = plt.subplots(4, 4, figsize=(15, 15), constrained_layout=True)
    for ax in axs.flat[len(TINT):]:
        ax.axis("off")
    for ax, k in zip(axs.flat, TINT):
        r, frac, p95 = maps[k]
        im = ax.imshow(r, origin="lower", extent=ext, cmap="RdBu_r", vmin=-0.6, vmax=0.6)
        ax.contour(np.arange(NX) * DX / 1e3 + 1, np.arange(NY) * DX / 1e3 + 1, np.abs(r), levels=[RC], colors="k", linewidths=0.4)
        box(ax)
        ax.set_title(f"t = {k} 時（有意 {frac * 100:.0f}%、偶然なら ≤ {p95 * 100:.0f}%）", loc="left", fontsize=10)
    fig.colorbar(im, ax=axs.flat[len(TINT) - 1], shrink=0.9, label="相関 r（負 = 湿っているほど雨が少ない）")
    fig.suptitle(f"時刻 t の土壌水分（0〜20 cm の平均）と、目標領域の雨（13〜17 時の合計）の相関。細線 = |r| = {RC}、黒枠 = 目標領域",
                 fontsize=12, x=0.01, ha="left")
    fig.savefig(f"{out}/soil_corr_all_S20.png", dpi=100)
    print(f"\n図: {out}/soil_cov_all_summary.png, soil_corr_all_S20.png")


if __name__ == "__main__":
    main()
