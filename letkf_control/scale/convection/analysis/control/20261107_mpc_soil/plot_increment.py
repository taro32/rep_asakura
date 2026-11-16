#!/usr/bin/env python3
"""MPC（土壌水分の逐次制御）で、どこでどれだけ土壌水分を増やしたかの図（2026-11-16）

介入した cycle（obsdepcont が空でない cycle）ごとに、LAND_WATER の第 1 層の増分 Δθ = anal − gues を地図にする。
LAND_WATER は LETKF では変わらないので、anal − gues がそのまま制御の増分。member は RELAX_ALPHA = 1 なので平均の移動だけで、
member の増分は anal/mean − gues/mean とみな同じ（member 個別のファイルは HIST_CLEAN で消えている）。

図 1（実験ごと、increment_<実験名>.png）: 行 = 介入した cycle、列 =
  a. mdet の Δθ、b. member 平均の Δθ、c. Δθ_mdet / σ（σ は gues/sprd の第 1 層）
  - 色の範囲はパネルごと（0〜そのパネルの 99 パーセンタイル。cycle で桁が違ううえ、max は少数の点で決まるため）。max は各パネルに書く
  - 灰色: 戻した点（mdet の増分が 0。乾かす向きだったので第一推定に戻した点）
  - 四角: 目標領域、等値線: 修正のあとの mdet の予報で Y の窓（t + T_c ± 15 分）に降った雨 [mm]
    （第一推定の history は残っていないので、修正のあとの予報で代える）
図 2（increment_amount.png）: 足した水の量（第 1・2 層。Σ Δθ × 層の厚さ × 1000 [mm]）を、全体の平均と目標領域の平均で、cycle ごとに

使い方: cd analysis && FIGDIR=../docs/control/20261107_mpc_soil [CACHE=<読んだ値を置く場所>] python3 control/20261107_mpc_soil/plot_increment.py [--base …/mpc_soil] [--runs r080 p3_tc1 p3_tc3]
  読み込み（144 ファイル × 5 種類 × cycle と history）は 1 実験 数分かかる。CACHE を指定すると読んだ値を CACHE/increment_<実験名>.npz に置き、次からはそれを使う
"""
import argparse
import glob
import os
import sys

import numpy as np
import netCDF4

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_letkc_ctl_test import XC, YC, HALF  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))   # analysis/common.py
import common as cm  # noqa: E402

DZ = np.array([0.05, 0.15])   # 第 1・2 層の厚さ [m]（lz の中心 0.025・0.125 m から）
HALF_T = 900.0                # Y の窓 t + T_c ± 15 分
NX = NY = cm.NX


def read_params(rundir):
    p = {}
    with open(f"{rundir}/params.txt") as f:
        for line in f:
            if "=" in line:
                k, v = line.rstrip("\n").split("=", 1)
                p[k] = v
    return p


def read_land_water(d, T):
    """時刻 T の restart（init_<T>.pe*.nc）の LAND_WATER の第 1・2 層を全体の格子に並べる → (2, NY, NX)
    （T_c = 3 時間の実験では gues・anal の下に予報の途中の時刻の restart もあるので、時刻で選ぶ）"""
    out = np.full((2, NY, NX), np.nan)
    fs = sorted(glob.glob(f"{d}/init_{T[:8]}-{T[8:]}.000.pe*.nc"))
    assert len(fs) == 144, (d, len(fs))
    for f in fs:
        with netCDF4.Dataset(f) as nc:
            i, j = cm._ij(nc)
            v = nc["LAND_WATER"][:].data   # (y, x, lz)
            out[:, j[0]:j[-1] + 1, i[0]:i[-1] + 1] = np.moveaxis(v[:, :, :2], 2, 0)
    assert not np.isnan(out).any(), d
    return out


def read_rain(histdir, tc):
    """修正のあとの予報の history から、Y の窓（t + tc ± 15 分）の積算 [mm] の地図。PREC は 5 分平均（time は区間の終わり）"""
    out = np.full((NY, NX), np.nan)
    for f in sorted(glob.glob(f"{histdir}/history.pe*.nc")):
        with netCDF4.Dataset(f) as nc:
            i, j = cm._ij(nc)
            t = nc["time"][:].data
            t = t - t[0]
            k = (t > tc - HALF_T + 1e-3) & (t <= tc + HALF_T + 1e-3)
            assert k.sum() == 6, (f, t)
            out[j[0]:j[-1] + 1, i[0]:i[-1] + 1] = nc["PREC"][:].data[k].sum(axis=0) * 300.0
    assert not np.isnan(out).any(), histdir
    return out


def ctl_times(rundir):
    return [os.path.basename(f)[11:25] for f in sorted(glob.glob(f"{rundir}/obsdep/obsdepcont_*.dat")) if os.path.getsize(f) > 0]


def load(rundir, tc):
    c = os.environ.get("CACHE")
    fn = f"{c}/increment_{os.path.basename(rundir)}.npz" if c else None
    if fn and os.path.exists(fn):
        z = np.load(fn)
        return {T: {k: z[f"{T}_{k}"] for k in ("dmdet", "dmean", "sprd", "rain")} for T in z["times"]}
    res = {}
    for T in ctl_times(rundir):
        g = {m: read_land_water(f"{rundir}/{T}/gues/{m}", T) for m in ("mdet", "mean", "sprd")}
        a = {m: read_land_water(f"{rundir}/{T}/anal/{m}", T) for m in ("mdet", "mean")}
        res[T] = dict(dmdet=a["mdet"] - g["mdet"], dmean=a["mean"] - g["mean"], sprd=g["sprd"],
                      rain=read_rain(f"{rundir}/{T}/hist/mdet", tc))
    if fn:
        os.makedirs(c, exist_ok=True)
        np.savez(fn, times=np.array(list(res)), **{f"{T}_{k}": v for T, r in res.items() for k, v in r.items()})
    return res


def target_mask():
    xc = (np.arange(NX) + 0.5) * cm.DX
    yc = (np.arange(NY) + 0.5) * cm.DX
    return (np.abs(yc[:, None] - YC) <= HALF + 1e-3) & (np.abs(xc[None, :] - XC) <= HALF + 1e-3)


def water_mm(d):   # (2, NY, NX) の Δθ → 足した水 [mm]
    return (d * DZ[:, None, None]).sum(axis=0) * 1000.0


def summary(name, res):
    tm = target_mask()
    print(f"\n[{name}]  足した水（第 1・2 層）[mm]: 全体の平均 / 目標領域の平均、第 1 層の max Δθ、max Δθ/σ、増えた点 / 戻した点（mdet、第 1 層）")
    rows = []
    for T, r in res.items():
        wd, we = water_mm(r["dmdet"]), water_mm(r["dmean"])
        d1 = r["dmdet"][0]
        with np.errstate(divide="ignore", invalid="ignore"):
            z = np.where(r["sprd"][0] > 0, d1 / r["sprd"][0], np.nan)
        row = dict(T=T, wd_all=wd.mean(), wd_tgt=wd[tm].mean(), we_all=we.mean(), we_tgt=we[tm].mean(),
                   max1=np.abs(d1).max(), maxz=np.nanmax(np.abs(z)), npos=(d1 > 0).sum(), nzero=(d1 == 0).sum(), nneg=(d1 < 0).sum())
        rows.append(row)
        print(f"  {T[8:10]} 時  mdet {row['wd_all']:.4f} / {row['wd_tgt']:.4f}   mean {row['we_all']:.4f} / {row['we_tgt']:.4f}   "
              f"max Δθ {row['max1']:.2e}  member 平均の min Δθ {r['dmean'][0].min():.2e}  max Δθ/σ {row['maxz']:.3f}  増 {row['npos']} / 戻 {row['nzero']}（負 {row['nneg']}）")
    return rows


def plot_maps(name, res, tc, figd):
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap
    from matplotlib.patches import Rectangle
    cmap = ListedColormap(plt.get_cmap("Blues")(np.linspace(0.15, 1.0, 256)))   # 白に近い色から（灰色の「戻した点」と分ける）
    n = len(res)
    fig, axs = plt.subplots(n, 3, figsize=(13, 4.0 * n + 0.6), squeeze=False, constrained_layout=True)
    ext = [0, NX * cm.DX / 1e3, 0, NY * cm.DX / 1e3]
    xc = (np.arange(NX) + 0.5) * cm.DX / 1e3
    yc = (np.arange(NY) + 0.5) * cm.DX / 1e3
    lev = [0.5, 2.0, 5.0]
    for k, (T, r) in enumerate(res.items()):
        d1, e1, s1 = r["dmdet"][0], r["dmean"][0], r["sprd"][0]
        with np.errstate(divide="ignore", invalid="ignore"):
            z = np.where(s1 > 0, d1 / s1, np.nan)
        back = d1 == 0
        for c, (fld, ttl, unit) in enumerate(((d1, "mdet の Δθ", ""), (e1, "member 平均の Δθ", ""), (z, "Δθ_mdet / σ", ""))):
            ax = axs[k, c]
            vmax = np.nanmax(np.abs(fld))
            vmax = vmax if vmax > 0 else 1.0
            v99 = np.nanpercentile(np.abs(fld[~back]), 99) if (~back).any() else vmax
            v99 = v99 if v99 > 0 else vmax
            if c == 1:   # member 平均は、向きを mdet で判定するので負もありうる → 正負の色
                im = ax.imshow(np.where(back, np.nan, fld), origin="lower", extent=ext, cmap="RdBu", vmin=-v99, vmax=v99, interpolation="nearest", zorder=1)
            else:
                im = ax.imshow(np.where(back, np.nan, fld), origin="lower", extent=ext, cmap=cmap, vmin=0, vmax=v99, interpolation="nearest", zorder=1)
            ax.imshow(np.where(back, 1.0, np.nan), origin="lower", extent=ext, cmap=ListedColormap(["#c8c8c8"]), interpolation="nearest", zorder=1)
            cs = ax.contour(xc, yc, r["rain"], levels=lev, colors=["#f4a582", "#d6604d", "#8b0000"], linewidths=[0.8, 1.1, 1.4], zorder=3)
            ax.add_patch(Rectangle(((XC - HALF) / 1e3, (YC - HALF) / 1e3), 2 * HALF / 1e3, 2 * HALF / 1e3, fill=False, ec="w", lw=1.6, zorder=4))
            ax.add_patch(Rectangle(((XC - HALF) / 1e3, (YC - HALF) / 1e3), 2 * HALF / 1e3, 2 * HALF / 1e3, fill=False, ec="k", lw=0.8, ls="--", zorder=5))
            fig.colorbar(im, ax=ax, shrink=0.85, extend="both" if c == 1 else "max", format="%.1e" if c < 2 else "%.3f")
            if c == 1:
                ttl += f"\n（min {np.nanmin(fld):.2e}、max {np.nanmax(fld):.2e}）"
            else:
                ttl += f"\n（max {vmax:.2e}）" if c == 0 else f"\n（max {vmax:.3f}）"
            ax.set_title(f"t = {T[8:10]} 時  {ttl}", loc="left", fontsize=10)
            ax.set_aspect("equal")
            if k == n - 1:
                ax.set_xlabel("x [km]")
            if c == 0:
                ax.set_ylabel("y [km]")
    tcm = tc / 60
    fig.suptitle(f"{name}：LAND_WATER 第 1 層の増分 Δθ = anal − gues [m³/m³]\n色の範囲はパネルごとに |値| の 99 パーセンタイルまで（member 平均は負もあるので青 = 正、赤 = 負）。灰色: 戻した点（増分 0）、"
                 f"四角: 目標領域\n赤の等値線: 修正のあとの mdet の予報で t+{(tc - HALF_T) / 60:.0f}〜{(tc + HALF_T) / 60:.0f} 分（Y の窓）に降った雨 "
                 f"{', '.join(f'{v:g}' for v in lev)} mm（T_c = {tcm:.0f} 分）", fontsize=10, x=0.01, ha="left")
    fn = f"{figd}/increment_{name}.png"
    fig.savefig(fn, dpi=100)
    plt.close(fig)
    print(f"図: {fn}")


def plot_amount(allrows, figd):
    import matplotlib.pyplot as plt
    fig, axs = plt.subplots(1, 3, figsize=(15, 4.2), constrained_layout=True)
    cols = dict(zip(allrows, (cm.C1, cm.C2, cm.C3, cm.GRAY)))
    for name, (rows, lab) in allrows.items():
        h = np.array([int(r["T"][8:10]) for r in rows])
        c = cols[name]
        axs[0].plot(h, [r["wd_all"] for r in rows], "o-", color=c, label=f"{lab}: mdet")
        axs[0].plot(h, [r["we_all"] for r in rows], "s--", color=c, mfc="none", label=f"{lab}: member 平均")
        axs[1].plot(h, [r["wd_tgt"] for r in rows], "o-", color=c, label=f"{lab}: mdet")
        axs[1].plot(h, [r["we_tgt"] for r in rows], "s--", color=c, mfc="none", label=f"{lab}: member 平均")
        axs[2].plot(h, [r["maxz"] for r in rows], "o-", color=c, label=lab)
    for ax, t in zip(axs, ("足した水（第 1・2 層）、全体の平均 [mm]（±1E−3 の内側は線形）", "足した水（第 1・2 層）、目標領域の平均 [mm]（同上）", "第 1 層の max Δθ_mdet / σ")):
        ax.set_title(t, loc="left", fontsize=10)
        ax.set_yscale("symlog", linthresh=1e-3 if "mm" in t else 1e-2)
        ax.axhline(0, color="0.3", lw=0.6)
        ax.set_xlabel("介入の時刻 t [h]")
        ax.grid(alpha=0.3, which="both")
        ax.set_xticks(range(12, 18))
    axs[0].legend(frameon=False, fontsize=8)
    fn = f"{figd}/increment_amount.png"
    fig.savefig(fn, dpi=100)
    plt.close(fig)
    print(f"図: {fn}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--base", default="/work/gv42/v42013/20260923_enkc_convection/mpc_soil")
    p.add_argument("--runs", nargs="+", default=["r080", "p3_tc1", "p3_tc3"])
    a = p.parse_args()
    import matplotlib
    matplotlib.use("Agg")
    cm.use_japanese_font()
    figd = cm.figdir()
    allrows = {}
    for name in a.runs:
        rundir = f"{a.base}/{name}"
        prm = read_params(rundir)
        tc = float(prm.get("TC", 3600))
        res = load(rundir, tc)
        allrows[name] = (summary(name, res), f"{name}（T_c = {tc / 3600:g} 時間）")
        plot_maps(name, res, tc, figd)
    plot_amount(allrows, figd)


if __name__ == "__main__":
    main()
