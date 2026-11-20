#!/usr/bin/env python3
"""LETKC の修正を論文の形に直した MPC（mpc_same）で、どこでどれだけ土壌水分を増やしたかの図（2026-11-18。docs/control/notes.md 3.11）

読み込み・集計は control/20261107_mpc_soil/plot_increment.py（load・summary）を使う。直したあとは mdet と member に同じ増分を足すので
（切り詰めた点を除く）、mdet の列と member 平均の列を並べる 20261107 版の地図の代わりに、λ = 0 と λ = 0.5 を横に並べる。

図 1（increment_maps.png）: 行 = 介入した cycle、列 = 実験ごとに [Δθ, Δθ / σ]（どれも LAND_WATER の第 1 層、mdet）
  - 色の範囲は行ごと・量ごとに実験で共通（0〜2 実験を合わせた |値| の 99 パーセンタイル）。max は各パネルに書く
  - 灰色: 増分 0 の点（向きの判定で戻した点と、λ で外した点）、四角: 目標領域
  - 赤の等値線: 修正のあとの mdet の予報で Y の窓に降った雨（0.5・2・5 mm）
図 2（increment_amount.png）: 20261107 版と同じ形（足した水の全体・目標領域の平均、max Δθ / σ）
標準出力: 20261107 版の summary に加えて、mdet と member 平均の増分の差（切り詰めた点の数と、それ以外での最大の差）

使い方: cd analysis && FIGDIR=../docs/control/20261116_mpc_same CACHE=/work/gv42/v42013/20260923_enkc_convection/mpc_same/increment_cache \
          python3 control/20261116_mpc_same/plot_increment.py [--runs mpc_same/p3_tc3 mpc_same/p3_tc3_l05] [--amount-also mpc_soil/p3_tc3]
  読み込みは 1 実験 5 分ほど（ログインノード）。CACHE を指定すると CACHE/increment_<実験名>.npz に置き、次からはそれを使う
  （--amount-also の実験は図 2 だけに足す。その CACHE は 20261107 版の mpc_soil/increment_cache を使う）
"""
import argparse
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "20261107_mpc_soil"))
import plot_increment as pi07  # noqa: E402
from check_letkc_ctl_test import XC, YC, HALF  # noqa: E402

sys.path.insert(0, os.path.join(HERE, "..", ".."))   # analysis/common.py
import common as cm  # noqa: E402

ROOT = "/work/gv42/v42013/20260923_enkc_convection"
CACHE07 = f"{ROOT}/mpc_soil/increment_cache"
LABEL = {
    "mpc_same/p3_tc3": "λ = 0",
    "mpc_same/p3_tc3_l05": "λ = 0.5",
    "mpc_soil/p3_tc3": "λ = 0（直す前）",
}


def load_run(rel, cache):
    rundir = f"{ROOT}/{rel}"
    tc = float(pi07.read_params(rundir).get("TC", 3600))
    old = os.environ.get("CACHE")
    if cache:
        os.environ["CACHE"] = cache
    try:
        return pi07.load(rundir, tc), tc
    finally:
        if old is None:
            os.environ.pop("CACHE", None)
        else:
            os.environ["CACHE"] = old


def check_same(rel, res):
    """mdet と member 平均の増分が、切り詰めた点を除いて同じか"""
    print(f"[{rel}] mdet − member 平均の増分（第 1・2 層）:")
    for T, r in res.items():
        d = np.abs(r["dmdet"] - r["dmean"])
        nclip = (d > 1e-9).sum()
        print(f"  {T[8:10]} 時  差が 1E−9 を超える点 {nclip}（切り詰めの点）、それ以外の最大の差 {d[d <= 1e-9].max():.1e}、全体の最大 {d.max():.2e}")


def plot_maps(runs, data, tc, figd):
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap
    from matplotlib.patches import Rectangle
    cmap = ListedColormap(plt.get_cmap("Blues")(np.linspace(0.15, 1.0, 256)))
    times = sorted(set.intersection(*[set(data[n]) for n in runs]))
    nr, nc = len(times), 2 * len(runs)
    fig, axs = plt.subplots(nr, nc, figsize=(4.3 * nc, 3.9 * nr + 0.9), squeeze=False, constrained_layout=True)
    ext = [0, cm.NX * cm.DX / 1e3, 0, cm.NY * cm.DX / 1e3]
    xc = (np.arange(cm.NX) + 0.5) * cm.DX / 1e3
    yc = (np.arange(cm.NY) + 0.5) * cm.DX / 1e3
    lev = [0.5, 2.0, 5.0]
    for k, T in enumerate(times):
        flds = {}
        for n in runs:
            r = data[n][T]
            d1, s1 = r["dmdet"][0], r["sprd"][0]
            with np.errstate(divide="ignore", invalid="ignore"):
                z = np.where(s1 > 0, d1 / s1, np.nan)
            flds[n] = (d1, z, d1 == 0, r["rain"])
        vm = []
        for q in (0, 1):   # 行ごと・量ごとに実験で共通の色の範囲
            v = np.concatenate([np.abs(flds[n][q][~flds[n][2]]).ravel() for n in runs])
            v = v[np.isfinite(v)]
            vm.append(np.percentile(v, 99) if v.size and np.percentile(v, 99) > 0 else 1.0)
        for i, n in enumerate(runs):
            d1, z, back, rain = flds[n]
            for q, (fld, ttl, fmt) in enumerate(((d1, "Δθ", "%.1e"), (z, "Δθ / σ", "%.3f"))):
                ax = axs[k, 2 * i + q]
                im = ax.imshow(np.where(back, np.nan, fld), origin="lower", extent=ext, cmap=cmap, vmin=0, vmax=vm[q], interpolation="nearest", zorder=1)
                ax.imshow(np.where(back, 1.0, np.nan), origin="lower", extent=ext, cmap=ListedColormap(["#c8c8c8"]), interpolation="nearest", zorder=1)
                ax.contour(xc, yc, rain, levels=lev, colors=["#f4a582", "#d6604d", "#8b0000"], linewidths=[0.8, 1.1, 1.4], zorder=3)
                for ec, lw, ls in (("w", 1.6, "-"), ("k", 0.8, "--")):
                    ax.add_patch(Rectangle(((XC - HALF) / 1e3, (YC - HALF) / 1e3), 2 * HALF / 1e3, 2 * HALF / 1e3, fill=False, ec=ec, lw=lw, ls=ls, zorder=4))
                if q == 1 or i == len(runs) - 1:
                    fig.colorbar(im, ax=ax, shrink=0.85, extend="max", format=fmt)
                mx = np.nanmax(np.abs(fld))
                ax.set_title(f"t = {T[8:10]} 時  {LABEL.get(n, n)}：{ttl}\n（max {mx:{'.2e' if q == 0 else '.3f'}}、増分のある点 {(~back).sum():,}）",
                             loc="left", fontsize=9.5)
                ax.set_aspect("equal")
                if k == nr - 1:
                    ax.set_xlabel("x [km]")
                if i == 0 and q == 0:
                    ax.set_ylabel("y [km]")
    fig.suptitle(f"LAND_WATER 第 1 層の増分 Δθ = anal − gues [m³/m³]（mdet。直したあとは member にも同じ増分）と Δθ / σ（σ = gues/sprd）\n"
                 f"色の範囲は行ごと・量ごとに 2 実験で共通（|値| の 99 パーセンタイルまで）。灰色: 増分 0（戻した点・λ で外した点）、四角: 目標領域\n"
                 f"赤の等値線: 修正のあとの mdet の予報で t+{(tc - 900) / 60:.0f}〜{(tc + 900) / 60:.0f} 分（Y の窓）に降った雨 {', '.join(f'{v:g}' for v in lev)} mm",
                 fontsize=10, x=0.01, ha="left")
    fn = f"{figd}/increment_maps.png"
    fig.savefig(fn, dpi=95)
    plt.close(fig)
    print(f"図: {fn}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--runs", nargs="+", default=["mpc_same/p3_tc3", "mpc_same/p3_tc3_l05"])
    p.add_argument("--amount-also", nargs="*", default=["mpc_soil/p3_tc3"])
    a = p.parse_args()
    import matplotlib
    matplotlib.use("Agg")
    cm.use_japanese_font()
    figd = cm.figdir()
    data, allrows, tcs = {}, {}, set()
    for rel in a.runs + a.amount_also:
        res, tc = load_run(rel, os.environ.get("CACHE") if rel in a.runs else CACHE07)
        tcs.add(tc)
        allrows[rel] = (pi07.summary(rel, res), LABEL.get(rel, rel))
        if rel in a.runs:
            data[rel] = res
            check_same(rel, res)
    assert len(tcs) == 1, tcs
    plot_maps(a.runs, data, tcs.pop(), figd)
    pi07.plot_amount(allrows, figd)


if __name__ == "__main__":
    main()
