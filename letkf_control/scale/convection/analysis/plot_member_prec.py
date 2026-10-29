#!/usr/bin/env python3
"""member ごとの積算降水を比べる（Phase 8 の 24 時間、2026-10-28。「すべての道が豪雨に通じていないか」）。

各 cycle の 1 時間予報の history（<OUTDIR>/<t>/hist/<mem>）の地上降水強度 PREC [kg/m²/s = mm/s] を、600〜3600 s の 6 時刻 × 600 s で足して
1 時間の降水量にし、時間窓 [H0, H1) 時間の分を積算する（0 s は前の cycle の 3600 s と重なるので除く。10 分ごとの瞬間値からの近似）。
member の領域平均の積算降水 ΣP で並べ、大きい 2 つ・真ん中の 2 つ・小さい 2 つの地図を描く。色の段は、全 member の格子点の積算降水の分布から決める。

使い方: cd analysis && STIME=20000131000000 OUTDIR=… FIGDIR=… python3 plot_member_prec.py [H0（既定 12）] [H1（既定 24）] [member 数（既定 80）]
出力: FIGDIR/member_prec_<H0>-<H1>h.png（地図 6 枚）・member_prec_<H0>-<H1>h_sorted.png（全 member の ΣP）・.npz（積算降水の地図）
"""
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import BoundaryNorm

import common as cm
from common import DX, NX, NY, tstr

H0 = int(sys.argv[1]) if len(sys.argv) > 1 else 12
H1 = int(sys.argv[2]) if len(sys.argv) > 2 else 24
NMEM = int(sys.argv[3]) if len(sys.argv) > 3 else 80
MEMS = [f"{m:04d}" for m in range(1, NMEM + 1)] + ["mdet"]
DT = 600.0                                          # history の間隔 [s]

cm.use_japanese_font()


def accumulate(mem):
    """mem の [H0, H1) 時間の積算降水 [mm]（NY, NX）。"""
    tot = np.zeros((NY, NX))
    for k in range(H0, H1):
        p = cm.read_hist(cm.hist_dir(mem, tstr(k)), ["PREC"], t=None)["PREC"]       # (時刻, NY, NX)
        tt = cm.hist_time(cm.hist_dir(mem, tstr(k)))
        if np.isnan(p).any() or not np.allclose(tt, np.arange(0, 3601, DT)):
            sys.exit(f"{mem} の {tstr(k)} の history が欠けている（time = {tt}）")
        tot += p[1:].sum(axis=0) * DT
    return tot


def nice(x):
    """色の段の切れ目を、1・2・5 × 10^n の近い値に丸める。"""
    e = 10 ** np.floor(np.log10(x))
    return min((1, 2, 5, 10), key=lambda m: abs(m * e - x)) * e


def main():
    out = cm.figdir()
    tag = f"{H0}-{H1}h"
    cache = f"{out}/member_prec_{tag}.npz"
    if os.path.exists(cache):
        acc = dict(np.load(cache))
    else:
        with ProcessPoolExecutor(max_workers=8) as ex:
            acc = dict(zip(MEMS, ex.map(accumulate, MEMS)))
        np.savez_compressed(cache, **acc)
    ens = MEMS[:-1]
    sp = np.array([acc[m].mean() for m in ens])        # 領域平均の積算降水 [mm]
    order = np.argsort(sp)[::-1]                       # 大きい順
    n = len(ens)
    picks = [("大きい", order[0]), ("大きい", order[1]), ("真ん中", order[n // 2 - 1]), ("真ん中", order[n // 2]),
             ("小さい", order[-2]), ("小さい", order[-1])]

    print(f"積算降水（{H0}〜{H1} 時間、領域平均 [mm]）: member の最小 {sp.min():.3f}・中央 {np.median(sp):.3f}・最大 {sp.max():.3f}、"
          f"mdet {acc['mdet'].mean():.3f}")
    for lab, i in picks:
        a = acc[ens[i]]
        print(f"  {lab}: member {ens[i]}  ΣP {sp[i]:.3f} mm、格子の最大 {a.max():.1f} mm、1 mm 以上の面積 {(a >= 1).mean() * 100:.1f}%")

    # 色の段: 全 member の格子点の積算降水のうち、降った所（0.1 mm 以上）の分布の分位点
    allv = np.concatenate([acc[m].ravel() for m in ens])
    wet = allv[allv >= 0.1]
    q = [nice(v) for v in np.percentile(wet, [10, 30, 50, 70, 85, 95, 99])] if wet.size else [1.0]
    levels = sorted(set([0.1] + [v for v in q if v > 0.1]))
    levels.append(nice(max(allv.max(), levels[-1] * 2)) if allv.max() > levels[-1] else levels[-1] * 2)
    cmap = plt.get_cmap("YlGnBu", len(levels) - 1).with_extremes(under="white", over="#3f007d")
    norm = BoundaryNorm(levels, cmap.N)
    print(f"色の段 [mm]: {levels}")

    ext = [0, NX * DX / 1e3, 0, NY * DX / 1e3]
    fig, axs = plt.subplots(2, 3, figsize=(13, 8.6), constrained_layout=True)
    for c, grp in enumerate(["大きい", "真ん中", "小さい"]):
        for r, (lab, i) in enumerate([p for p in picks if p[0] == grp]):
            ax = axs[r, c]
            im = ax.imshow(acc[ens[i]], origin="lower", extent=ext, cmap=cmap, norm=norm)
            ax.set_title(f"ΣP が{grp}: member {ens[i]}（順位 {int(np.flatnonzero(order == i)[0]) + 1}/{n}）\n"
                         f"領域平均 {sp[i]:.2f} mm・最大 {acc[ens[i]].max():.0f} mm", fontsize=10, loc="left")
            ax.set_xticks(np.arange(0, 241, 60))
            ax.set_yticks(np.arange(0, 241, 60))
            if r == 1:
                ax.set_xlabel("x [km]")
            if c == 0:
                ax.set_ylabel("y [km]")
    fig.colorbar(im, ax=axs, shrink=0.8, extend="both", label=f"{H0}〜{H1} 時間の積算降水 [mm]（白 = 0.1 mm 未満）")
    fig.suptitle(f"member ごとの積算降水（{H0}〜{H1} 時間、{n} member）。列: 領域平均 ΣP が大きい・真ん中・小さい member を 2 つずつ",
                 fontsize=12, x=0.01, ha="left")
    fig.savefig(f"{out}/member_prec_{tag}.png", dpi=110)

    fig, ax = plt.subplots(figsize=(10, 3.8), constrained_layout=True)
    ax.bar(np.arange(1, n + 1), sp[order], color=cm.GRAY, width=0.8)
    for lab, i in picks:
        k = int(np.flatnonzero(order == i)[0]) + 1
        ax.bar(k, sp[i], color=cm.C2, width=0.8)
        ax.text(k, sp[i], ens[i], ha="center", va="bottom", fontsize=7, rotation=90)
    ax.axhline(acc["mdet"].mean(), color="k", lw=1, ls="--", label=f"mdet（{acc['mdet'].mean():.2f} mm）")
    ax.set_xlabel("順位（ΣP の大きい順）")
    ax.set_ylabel("領域平均の積算降水 ΣP [mm]")
    ax.set_title(f"{H0}〜{H1} 時間の ΣP（全 {n} member。橙 = 地図を描いた member）", fontsize=11, loc="left")
    ax.set_xlim(0, n + 1)
    ax.legend(frameon=False)
    ax.grid(alpha=0.3, axis="y")
    lo, hi = min(sp.min(), acc["mdet"].mean()), max(sp.max(), acc["mdet"].mean())
    ax.set_ylim(lo - 0.15 * (hi - lo), hi + 0.25 * (hi - lo))      # 差が見えるように、縦軸はデータの範囲に合わせる（0 からではない）
    ax.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(integer=True))
    fig.savefig(f"{out}/member_prec_{tag}_sorted.png", dpi=110)
    print(f"図: {out}/member_prec_{tag}.png, member_prec_{tag}_sorted.png")


if __name__ == "__main__":
    main()
