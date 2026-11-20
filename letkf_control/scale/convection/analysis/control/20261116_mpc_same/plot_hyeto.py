#!/usr/bin/env python3
"""LETKC の修正を論文の形に直した MPC（mpc_same）の、目標領域のハイエトグラフ（2026-11-18。docs/control/notes.md 3.11）

各 cycle t の hist/mdet/（解析・制御のあとの予報し直し。PREC は 5 分平均）から、目標領域（中心 ±10 km）で平均した雨を読み、
t〜t+60 分をつないで 12〜18 時の実現した雨にする（読み込みは control/20261107_mpc_soil/compare_mpc_soil.py の area_acc）。

図（FIGDIR/hyeto_<FIGNAME>.png。既定 hyeto.png）:
  上: 5 分ごとの降水強度 [mm/h]（各 5 分の値を区間の終わりの時刻に置いて線でつなぐ。20261107 版と同じ。最後の cycle の t+60 分より先の予報は細い破線）
  中: 12 時からの積算 [mm]
  下: 介入した cycle ごとの制御目標: 修正前の member の Ȳ ± σ_Y と y*（その実験の obsdepcont）、修正のあとの mdet の Y
実験は --root からの相対パスで渡す（mpc_same/ と mpc_soil/ の実験を並べるため）。名前に nocontrol を含む実験は制御なしとして黒で描く。

使い方: cd analysis && FIGDIR=../docs/control/20261116_mpc_same python3 control/20261116_mpc_same/plot_hyeto.py \
          [--runs mpc_same/p3_tc3 mpc_same/p3_tc3_l05 mpc_soil/p3_tc3 mpc_soil/nocontrol] [--tc 10800]
  ログインノードで 1 分ほど
"""
import argparse
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "20261107_mpc_soil"))
import compare_mpc_soil as cms  # noqa: E402

sys.path.insert(0, os.path.join(HERE, "..", ".."))   # analysis/common.py
import common as cm  # noqa: E402

LABEL = {   # 凡例の名前（ないものは相対パスのまま）
    "mpc_same/p3_tc3": "λ = 0（同じ増分）",
    "mpc_same/p3_tc3_l05": "λ = 0.5（同じ増分）",
    "mpc_soil/p3_tc3": "λ = 0（直す前: mdet は自分の差）",
    "mpc_soil/nocontrol": "制御なし",
}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", default="/work/gv42/v42013/20260923_enkc_convection")
    p.add_argument("--runs", nargs="+", default=["mpc_same/p3_tc3", "mpc_same/p3_tc3_l05", "mpc_soil/p3_tc3", "mpc_soil/nocontrol"])
    p.add_argument("--tc", type=float, default=10800.0)
    p.add_argument("--start", type=int, default=12)
    p.add_argument("--last", type=int, default=18)
    a = p.parse_args()
    cms.TC = a.tc
    times = [f"20000131{h:02d}0000" for h in range(a.start, a.last)]

    res = {}
    for n in a.runs:
        for T in times:
            res[n, T] = cms.area_acc(f"{a.root}/{n}/{T}/hist/mdet")              # (Y, t〜t+60 分の積算)
            res[n, T, "ctl"] = cms.read_ctl(f"{a.root}/{n}/obsdep/obsdepcont_{T}.dat")   # (y*, σ_R, Ȳ) か None

    print(f"目標領域の平均。R1h = t〜t+60 分の積算 [mm]（mdet）、Y = t+{(a.tc - 900) / 60:.0f}〜{(a.tc + 900) / 60:.0f} 分の積算 [mm]（mdet、修正のあとの予報）")
    print(f"{'t':>3} " + " ".join(f"{n:>22}" for n in a.runs))
    for T in times:
        print(f"{T[8:10]:>3} " + " ".join(f"{res[n, T][1]:10.4f} {res[n, T][0]:11.4f}" for n in a.runs))
    tot = {n: sum(res[n, T][1] for T in times) for n in a.runs}
    print(f"{a.start}〜{a.last} 時の合計: " + ", ".join(f"{n} {tot[n]:.3f}" for n in a.runs))
    ref = next((n for n in a.runs if "nocontrol" in n), None)
    if ref:
        print("制御なしとの差: " + ", ".join(f"{n} {tot[n] - tot[ref]:+.3f} mm（{100 * (tot[n] / tot[ref] - 1):+.1f}%）" for n in a.runs if n != ref))
    for n in a.runs:
        cs = [(T, res[n, T, "ctl"]) for T in times if res[n, T, "ctl"] is not None]
        if cs:
            print(f"[{n}] obsdepcont: " + "  ".join(f"{T[8:10]} 時 Ȳ {c[2]:.4f} σ {c[1]:.4f} y* {c[0]:.4f} → Y_mdet {res[n, T][0]:.4f}" for T, c in cs))
    if os.environ.get("FIGDIR"):
        plot(a, times, res, tot)


def plot(a, times, res, tot):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    cm.use_japanese_font()
    figd = cm.figdir()
    cols = iter([cm.C1, cm.C2, cm.C3, cm.GRAY])
    sty = {n: ("k" if "nocontrol" in n else next(cols)) for n in a.runs}
    ctl_h = sorted({int(T[8:10]) for n in a.runs for T in times if res[n, T, "ctl"] is not None})

    fig, axs = plt.subplots(3, 1, figsize=(11, 12.5), constrained_layout=True, gridspec_kw=dict(height_ratios=[3, 2, 2.4]))
    for ax in axs[:2]:
        for h in ctl_h:
            ax.axvline(h, color="0.6", lw=0.6, ls=":")
    for n in a.runs:
        c, lab = sty[n], LABEL.get(n, n)
        tt, pp = [], []
        for T in times:
            t, pr = cms.SER[f"{a.root}/{n}/{T}/hist/mdet"]
            h = int(T[8:10]) + t / 3600.0
            m = t <= 3600 + 1e-3
            tt += list(h[m]); pp += list(pr[m])
            if T == times[-1] and (~m).any():
                axs[0].plot(h[~m | (t == 3600)], pr[~m | (t == 3600)], color=c, lw=0.8, ls="--", alpha=0.7)
        tt, pp = np.array(tt), np.array(pp)
        lw = 1.2 if "nocontrol" in n else 1.6
        axs[0].plot(tt, pp, color=c, lw=lw, label=f"{lab}：{a.start}〜{a.last} 時の合計 {tot[n]:.2f} mm")
        axs[1].plot(np.r_[a.start, tt], np.r_[0, np.cumsum(pp / 12.0)], color=c, lw=lw, label=lab)
    axs[0].set_ylabel("目標領域の降水強度 [mm/h]")
    axs[0].set_title(f"mdet の目標領域の雨（5 分ごと。各 cycle の t〜t+60 分をつないだもの、破線は最後の cycle の残りの予報。点線は介入の時刻）",
                     loc="left", fontsize=10)
    axs[0].legend(frameon=False, fontsize=9, loc="upper left")
    axs[1].set_ylabel(f"{a.start} 時からの積算 [mm]")
    axs[1].set_title("積算", loc="left", fontsize=10)
    axs[1].legend(frameon=False, fontsize=9, loc="upper left")
    for ax in axs[:2]:
        ax.grid(alpha=0.3)
        ax.set_xlim(a.start, a.last + 0.25)   # 最後の cycle の残りの予報は先頭の 15 分だけ見せる
    axs[1].set_xlabel("時刻 [h]")

    ax = axs[2]   # 横軸は介入の時刻 t。実験ごとに少しずらす
    runs_c = [n for n in a.runs if any(res[n, T, "ctl"] is not None for T in times)]
    w = 0.8 / max(len(runs_c), 1)
    for k, n in enumerate(runs_c):
        c, lab = sty[n], LABEL.get(n, n)
        hs, cs = zip(*[(int(T[8:10]), (res[n, T, "ctl"], res[n, T][0])) for T in times if res[n, T, "ctl"] is not None])
        x = np.array(hs) - 0.4 + w * (k + 0.5)
        ystar = np.array([q[0][0] for q in cs]); sig = np.array([q[0][1] for q in cs]); yb = np.array([q[0][2] for q in cs])
        ym = np.array([q[1] for q in cs])
        ax.errorbar(x - 0.06, yb, yerr=sig, fmt="o", color=c, mfc="none", ms=5, capsize=3, lw=1, label=f"{lab}: 修正前の member の Ȳ ± σ_Y")
        ax.plot(x - 0.06, ystar, "_", color=c, ms=14, mew=2.5)
        ax.plot(x + 0.06, ym, "s", color=c, ms=6, label=f"{lab}: 修正のあとの mdet の Y")
    ax.plot([], [], "_", color="k", ms=14, mew=2.5, label="横棒: y* = 0.8 Ȳ")
    ax.set_xticks(ctl_h, [f"{h} 時\n（Y の窓 {h + a.tc / 3600:g} 時 ± 15 分）" for h in ctl_h])
    ax.set_xlim(ctl_h[0] - 0.5, ctl_h[-1] + 0.5)
    ax.set_ylabel(f"Y = t+{(a.tc - 900) / 60:.0f}〜{(a.tc + 900) / 60:.0f} 分の積算 [mm]")
    ax.set_title("介入した cycle ごとの制御目標", loc="left", fontsize=10)
    ax.grid(alpha=0.3, axis="y")
    ax.legend(frameon=False, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.22), ncol=2)
    ax.set_xlabel("介入の時刻 t")
    fn = os.environ.get("FIGNAME") or "hyeto.png"
    fig.savefig(f"{figd}/{fn}", dpi=110)
    print(f"図: {figd}/{fn}")


if __name__ == "__main__":
    main()
