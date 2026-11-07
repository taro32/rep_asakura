#!/usr/bin/env python3
"""土壌水分と目標領域の雨の共分散（下見、2026-11-02）。

制御は「時刻 t_int の土壌水分 u と、目標時刻の目標領域の雨 Y の共分散」で、どこを湿らせるかを決める。
その材料があるかを、Phase 8 の 80 member の結果（cycle の実験。途中で 1 時間ごとに同化が入る）で下見する。
- u: t_int（7〜12 時）の解析の restart（<OUTDIR>/<t>/anal/<mem>）の LAND_WATER の第 1 層。土壌水分は LETKF で更新しないので第一推定と同じ
- Y: 目標領域（x 70〜90 km・y 110〜130 km）の平均降水。plot_target_prec.py の npz から
    peak: 15〜16 時の 1 時間降水量 [mm]、total: 13〜17 時の合計 [mm]
- 出すもの: u の member 間のばらつき、u と Y の相関の地図、有意な相関の格子の割合（Y を並べ替えた 500 回と比べる）、
  目標領域の平均の u と Y の相関
80 member で偶然と区別できる相関の大きさ（両側 5%）は |r| > 0.22。

使い方: cd analysis && STIME=20000131000000 OUTDIR=… FIGDIR=… python3 control/20261102_soil_cov/check_soil_cov.py [member 数（既定 80）]
出力: 表（標準出力）と FIGDIR/soil_spread.png・soil_corr_peak.png・soil_corr_total.png・soil_cov.npz
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

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))   # analysis/common.py
import common as cm
from common import DX, NX, NY, tstr

NMEM = int(sys.argv[1]) if len(sys.argv) > 1 else 80
MEMS = [f"{m:04d}" for m in range(1, NMEM + 1)]
TINT = [7, 8, 9, 10, 11, 12]                        # t_int の候補 [h]（STIME から）
I0, J0, K = 35, 55, 10                              # 目標領域（plot_target_prec.py と同じ）
YNPZ = f"{cm.DOCS}/control/20261102_target_prec/target_prec.npz"
NPERM = 500
RC = 0.22                                           # N = 80 の両側 5% の相関

cm.use_japanese_font()


def read_member(mem):
    """mem の t_int ごとの LAND_WATER 第 1 層（len(TINT), NY, NX）。"""
    out = np.full((len(TINT), NY, NX), np.nan, dtype=np.float32)
    for n, k in enumerate(TINT):
        t = tstr(k)
        out[n] = cm.read_restart(cm.restart_dir("anal", mem, t), t=t, names=["LAND_WATER"])["LAND_WATER"][0]
    return out


def corr(u, y):
    """u（member, NY, NX）と y（member）の相関（NY, NX）。"""
    ua = u - u.mean(axis=0)
    ya = y - y.mean()
    return np.tensordot(ya, ua, axes=(0, 0)) / np.sqrt((ua ** 2).sum(axis=0) * (ya ** 2).sum())


def box(ax):
    ax.add_patch(Rectangle((I0 * DX / 1e3, J0 * DX / 1e3), K * DX / 1e3, K * DX / 1e3, fill=False, ec="k", lw=1.2))


def main():
    out = cm.figdir()
    cache = f"{out}/soil_cov.npz"
    if os.path.exists(cache):
        U = np.load(cache)["U"]
    else:
        with ProcessPoolExecutor(max_workers=8) as ex:
            U = np.array(list(ex.map(read_member, MEMS)))     # (member, t_int, NY, NX)
        np.savez_compressed(cache, U=U)
    if np.isnan(U).any():
        sys.exit("LAND_WATER に埋まらない格子点があります。")

    z = np.load(YNPZ)
    P = np.array([z[m] for m in MEMS])                        # (member, 10 分ごと) [mm/h]
    hr = P.reshape(len(MEMS), -1, 6).mean(axis=2)             # 1 時間降水量 [mm]
    Ys = {"peak": (hr[:, 15], "15〜16 時の 1 時間降水量"), "total": (hr[:, 13:17].sum(axis=1), "13〜17 時の合計")}
    for key, (y, lab) in Ys.items():
        print(f"Y（{lab}、目標領域の平均）: 平均 {y.mean():.2f} mm、標準偏差 {y.std():.2f} mm、範囲 {y.min():.2f}〜{y.max():.2f} mm")

    ext = [0, NX * DX / 1e3, 0, NY * DX / 1e3]
    sd = U.std(axis=0)                                        # (t_int, NY, NX)
    print("\n土壌水分（LAND_WATER 第 1 層 [m³/m³]）の member 間の標準偏差")
    print(" t_int  領域の中央値  領域の最大   目標領域の平均  （参考: member 平均の領域平均）")
    for n, k in enumerate(TINT):
        print(f" {k:3d} 時  {np.median(sd[n]):.4f}      {sd[n].max():.4f}     {sd[n][J0:J0 + K, I0:I0 + K].mean():.4f}"
              f"          {U[:, n].mean():.4f}")

    fig, axs = plt.subplots(1, 3, figsize=(14, 4.6), constrained_layout=True)
    im = axs[0].imshow(U[:, 0].mean(axis=0), origin="lower", extent=ext, cmap="YlGnBu", vmin=0.15, vmax=0.3)
    fig.colorbar(im, ax=axs[0], shrink=0.85, label="m³/m³")
    axs[0].set_title(f"(a) member 平均（{TINT[0]} 時）", loc="left", fontsize=11)
    vmax = float(np.percentile(sd, 99))
    for ax, n, ttl in [(axs[1], 0, "(b)"), (axs[2], len(TINT) - 1, "(c)")]:
        im = ax.imshow(sd[n], origin="lower", extent=ext, cmap="magma_r", vmin=0, vmax=vmax)
        ax.set_title(f"{ttl} member 間の標準偏差（{TINT[n]} 時）", loc="left", fontsize=11)
    fig.colorbar(im, ax=axs[1:], shrink=0.85, label="m³/m³")
    for ax in axs:
        box(ax)
        ax.set_xlabel("x [km]")
    axs[0].set_ylabel("y [km]")
    fig.suptitle("土壌水分（LAND_WATER 第 1 層）。黒枠 = 目標領域", fontsize=12, x=0.01, ha="left")
    fig.savefig(f"{out}/soil_spread.png", dpi=110)

    rng = np.random.default_rng(0)
    for key, (y, lab) in Ys.items():
        print(f"\nu（t_int の土壌水分）と Y（{lab}）の相関。有意 = |r| > {RC}（80 member、両側 5%）")
        print(" t_int  有意な格子の割合  並べ替え 500 回の割合の 95%  r の最小  r の最大   目標領域の平均の u との r")
        fig, axs = plt.subplots(2, 3, figsize=(13, 8.6), constrained_layout=True)
        for n, k in enumerate(TINT):
            r = corr(U[:, n], y)
            frac = (np.abs(r) > RC).mean()
            perm = np.array([(np.abs(corr(U[:, n], rng.permutation(y))) > RC).mean() for _ in range(NPERM)])
            ub = U[:, n, J0:J0 + K, I0:I0 + K].mean(axis=(1, 2))
            rb = np.corrcoef(ub, y)[0, 1]
            print(f" {k:3d} 時   {frac * 100:5.1f}%            {np.percentile(perm, 95) * 100:5.1f}%             "
                  f"{r.min():6.2f}  {r.max():6.2f}    {rb:6.2f}")
            ax = axs.flat[n]
            im = ax.imshow(r, origin="lower", extent=ext, cmap="RdBu_r", vmin=-0.6, vmax=0.6)
            ax.contour(np.arange(NX) * DX / 1e3 + 1, np.arange(NY) * DX / 1e3 + 1, np.abs(r), levels=[RC],
                       colors="k", linewidths=0.4)
            box(ax)
            ax.set_title(f"t_int = {k} 時（有意 {frac * 100:.0f}%、偶然なら ≤ {np.percentile(perm, 95) * 100:.0f}%）",
                         loc="left", fontsize=10)
        fig.colorbar(im, ax=axs, shrink=0.8, label="相関 r（負 = 湿っているほど雨が少ない）")
        fig.suptitle(f"t_int の土壌水分と、目標領域の雨（{lab}）の相関（80 member）。細線 = |r| = {RC}、黒枠 = 目標領域",
                     fontsize=12, x=0.01, ha="left")
        fig.savefig(f"{out}/soil_corr_{key}.png", dpi=110)
    print(f"\n図: {out}/soil_spread.png, soil_corr_peak.png, soil_corr_total.png")


if __name__ == "__main__":
    main()
