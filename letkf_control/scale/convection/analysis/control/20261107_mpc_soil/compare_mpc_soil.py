#!/usr/bin/env python3
"""MPC（土壌水分の逐次制御）の本番 r080 と制御なし nocontrol の比較（2026-11-07）

各 cycle t の hist/<mdet|mean>/（解析・制御のあとの予報し直し、t〜t+75 分、PREC は 5 分平均）から、目標領域（中心 ±10 km）で平均した
  - Y   : t+TC ± 15 分の積算（制御目標で使った量。既定 TC = 1 時間で t+45〜75 分）
  - R1h : t〜t+60 分の積算（次の cycle までに実際に降った分。cycle をつなぐと 12〜18 時の実現した雨）
を出す。r080 は obsdepcont から y*・σ_R も出す（Ȳ = y* − omb）。
FIGDIR を指定すると図 FIGDIR/mpc_target.png も出す（上: 目標領域の降水強度の時系列、下: cycle ごとの Y と y*・Ȳ ± σ_Y）。

使い方: cd analysis && [FIGDIR=…] python3 control/20261107_mpc_soil/compare_mpc_soil.py [--base …/mpc_soil] [--runs r080 nocontrol] [--tc 3600] [--start 12] [--last 18]
"""
import argparse
import glob
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check_letkc_ctl_test import XC, YC, HALF  # noqa: E402

import netCDF4  # noqa: E402

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))   # analysis/common.py
import common as cm  # noqa: E402

TIMES = []                  # 介入の時刻（main で --start〜--last − 1 時）
TC, HALF_T = 3600.0, 900.0  # Y の窓 t + TC ± HALF_T


_PES = None   # 目標領域にかかる pe のファイル名（領域分割はどの実験・cycle でも同じなので 1 回だけ探す）


def area_acc(histdir):
    """目標領域にかかる pe のファイルだけ読み、目標領域の格子の PREC を足し合わせる"""
    global _PES
    if _PES is None:
        _PES = []
        for f in sorted(glob.glob(f"{histdir}/history.pe*.nc")):
            with netCDF4.Dataset(f) as d:
                if (np.abs(d["x"][:].data - XC) <= HALF + 1e-3).any() and (np.abs(d["y"][:].data - YC) <= HALF + 1e-3).any():
                    _PES.append(os.path.basename(f))
    tot, ncell, t = None, 0, None
    for f in [f"{histdir}/{b}" for b in _PES]:
        with netCDF4.Dataset(f) as d:
            x, y = d["x"][:].data, d["y"][:].data
            mx = np.abs(x - XC) <= HALF + 1e-3
            my = np.abs(y - YC) <= HALF + 1e-3
            if not (mx.any() and my.any()):
                continue
            if t is None:
                t = d["time"][:].data
            v = d["PREC"][:].data[:, my][:, :, mx]
            tot = v.sum(axis=(1, 2)) if tot is None else tot + v.sum(axis=(1, 2))
            ncell += v.shape[1] * v.shape[2]
    assert ncell == 100, ncell
    t = t - t[0]
    s = tot / ncell * 300.0   # 各 5 分の積算（time は区間の終わり）
    k = (t > TC - HALF_T + 1e-3) & (t <= TC + HALF_T + 1e-3)
    y = s[k].sum() if k.sum() == 6 else np.nan   # 予報が Y の窓まで届かない（T_c = 3 時間で nocontrol の t+75 分の予報）なら nan
    r = s[(t > 1e-3) & (t <= 3600 + 1e-3)].sum()
    SER[histdir] = (t[1:], s[1:] * 12.0)   # 5 分ごとの降水強度 [mm/h]（time = 区間の終わり、t からの秒）
    return y, r


SER = {}


def read_ctl(f):
    if not os.path.exists(f) or os.path.getsize(f) == 0:
        return None
    b = np.fromfile(f, dtype="<f4")[1:-1]
    ystar, err, omb = b[4], b[5], b[9]
    return ystar, err, ystar - omb


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--base", default="/work/gv42/v42013/20260923_enkc_convection/mpc_soil")
    p.add_argument("--runs", nargs="+", default=["r080", "nocontrol"])
    p.add_argument("--tc", type=float, default=3600.0)
    p.add_argument("--start", type=int, default=12)
    p.add_argument("--last", type=int, default=18)
    a = p.parse_args()
    global TC
    TC = a.tc
    TIMES[:] = [f"20000131{h:02d}0000" for h in range(a.start, a.last)]
    ctlrun = next((n for n in a.runs if "nocontrol" not in n), None)
    res = {}
    for n in a.runs:
        for T in TIMES:
            for m in ("mdet", "mean"):
                res[n, T, m] = area_acc(f"{a.base}/{n}/{T}/hist/{m}")
            res[n, T, "ctl"] = read_ctl(f"{a.base}/{n}/obsdep/obsdepcont_{T}.dat")

    print(f"Y = 目標領域平均 PREC の t+{(TC - HALF_T) / 60:.0f}〜{(TC + HALF_T) / 60:.0f} 分積算 [mm]、R1h = t〜t+60 分積算 [mm]")
    hdr = f"{'t':>3} " + " ".join(f"{n+':'+k:>18}" for n in a.runs for k in ("Y_mdet", "Y_mean", "R1h_mdet"))
    print(hdr)
    tot = {n: 0.0 for n in a.runs}
    for T in TIMES:
        row = f"{T[8:10]:>3} "
        for n in a.runs:
            ym, _ = res[n, T, "mdet"]
            ye, _ = res[n, T, "mean"]
            r = res[n, T, "mdet"][1]
            tot[n] += r
            row += f"{ym:18.4f} {ye:18.4f} {r:18.4f} "
        print(row)
    print(f"{a.start}〜{a.last} 時の実現した雨（mdet、R1h の和）: " + ", ".join(f"{n} {tot[n]:.4f}" for n in a.runs))
    for n in a.runs:
        print(f"\n[{n}] obsdepcont（y*, σ_R, 制御前の Ȳ）")
        for T in TIMES:
            c = res[n, T, "ctl"]
            print(f"  {T[8:10]}: " + ("なし（棄却）" if c is None else f"y* {c[0]:.4f}  σ_R {c[1]:.4f}  Ȳ {c[2]:.4f}"))
    if os.environ.get("FIGDIR"):
        plot(a, res)


def plot(a, res):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    cm.use_japanese_font()
    figd = cm.figdir()
    tcl = f"T_c = {TC / 3600:g} 時間"
    ctlrun = next((n for n in a.runs if "nocontrol" not in n), None)
    def how(n):   # 介入した cycle（obsdepcont が空でない cycle）
        hs = [T[8:10] for T in TIMES if res[n, T, "ctl"] is not None]
        return "毎時介入" if len(hs) == len(TIMES) else "介入 " + "・".join(hs) + " 時"
    cols = iter([cm.C1, cm.C2])
    sty = {n: (("k", f"{n}（制御なし）") if "nocontrol" in n else (next(cols), f"{n}（y* = 0.8 Ȳ、{how(n)}）")) for n in a.runs}
    fig, axs = plt.subplots(2, 1, figsize=(11, 8), sharex=True, constrained_layout=True)

    ax = axs[0]
    for T in TIMES:
        ax.axvline(int(T[8:10]), color="0.6", lw=0.6, ls=":")
    for n in a.runs:
        c, lab = sty.get(n, ("0.4", n))
        tt, pp = [], []
        for k, T in enumerate(TIMES):
            t, pr = SER[f"{a.base}/{n}/{T}/hist/mdet"]
            h = int(T[8:10]) + t / 3600.0
            m = t <= 3600 + 1e-3
            tt += list(h[m]); pp += list(pr[m])
            if T == TIMES[-1]:   # 最後の cycle の t+60 分より先の予報（ほかの cycle は次の cycle と重なるので描かない）
                ax.plot(h[~m | (t == 3600)], pr[~m | (t == 3600)], color=c, lw=0.8, ls="--", alpha=0.7)
        ax.plot(tt, pp, color=c, lw=1.6, label=f"{lab}：{a.start}〜{a.last} 時の合計 {sum(res[n, T, 'mdet'][1] for T in TIMES):.2f} mm")
    ax.set_ylabel("目標領域の降水強度 [mm/h]")
    ax.set_title(f"mdet の目標領域の雨（{tcl}。実線: 各 cycle の t〜t+60 分をつないだもの、破線: 最後の cycle の残りの予報。点線は介入の時刻）", loc="left", fontsize=10)
    ax.grid(alpha=0.3)
    ax.legend(frameon=False, fontsize=9, loc="upper left")

    ax = axs[1]
    hc = np.array([int(T[8:10]) + TC / 3600 for T in TIMES])   # Y の窓の中心（t + T_c）
    ctl = [res[ctlrun, T, "ctl"] for T in TIMES] if ctlrun else None
    if ctl and any(c is not None for c in ctl):   # 介入しない cycle（CTL_HOURS の外）は obsdepcont が空なので描かない
        k = np.array([c is not None for c in ctl])
        ys, sr, yb = (np.array([c[i] for c in ctl if c is not None]) for i in range(3))
        ax.errorbar(hc[k] - 0.06, yb, yerr=sr, fmt="o", color=cm.GRAY, ms=5, capsize=3, label=f"{ctlrun} の member（修正前）: Ȳ ± σ_Y")
        ax.plot(hc[k] - 0.06, ys, "_", color=cm.C3, ms=16, mew=2.5, label="y* = 0.8 Ȳ")
    for n, dx, mk in zip(a.runs, (0.04, 0.12, 0.20), ("s", "D", "^")):
        if True:
            c, lab = sty[n]
            yy = [res[n, T, "mdet"][0] for T in TIMES]
            if np.isnan(yy).all():   # 予報が Y の窓まで届かない実験は描かない
                continue
            ax.plot(hc + dx, yy, mk, color=c, ms=5, label=f"{lab}: mdet の Y（修正のあとの予報）")
    ax.set_ylabel(f"Y = t+{(TC - HALF_T) / 60:.0f}〜{(TC + HALF_T) / 60:.0f} 分の積算 [mm]")
    ax.set_title(f"cycle ごとの制御目標（{tcl}。横軸は Y の窓の中心 t + T_c）", loc="left", fontsize=10)
    ax.grid(alpha=0.3)
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.set_xlabel(f"時刻 [h]（各 cycle は t + {(TC + HALF_T) / 60:.0f} 分まで予報）")
    ax.set_xlim(a.start, max(a.last, hc[-1]) + 0.5)
    fn = os.environ.get("FIGNAME") or ("mpc_target.png" if TC == 3600 else f"mpc_target_tc{TC / 3600:g}.png")
    fig.savefig(f"{figd}/{fn}", dpi=110)
    print(f"図: {figd}/{fn}")


if __name__ == "__main__":
    main()
