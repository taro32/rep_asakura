#!/usr/bin/env python3
"""EnKC の制御実験（control/20261103_enkc_once/make_control.py）の結果を見る（2026-11-03）。

各本の目標領域の雨（13〜14 時・13〜17 時の合計）と降り始めの時刻を、修正なし（none）と、予測 ΔY と比べる。
カオスの揺れの目安として、修正なしの流し直し（none）と、もとの mdet（phase9_patch_t08 の 0081）の差も出す。

使い方: cd analysis && FIGDIR=… python3 control/20261103_enkc_once/check_control.py [実験の場所（既定 …/phase9_control_t08）]
出力: 表（標準出力）と FIGDIR/control_target.png
"""
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from netCDF4 import Dataset

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))   # analysis/common.py
import common as cm

BASE = "/work/gv42/v42013/20260923_enkc_convection"
EXP = sys.argv[1] if len(sys.argv) > 1 else f"{BASE}/phase9_control_t08"
ORIG = f"{BASE}/phase9_patch_t08/hist/0081"         # もとの mdet（修正なし）
T0 = 8
I0, J0, K = 35, 55, 10
DT = 600.0
ONSET = 1.0                                          # 降り始めの基準 [mm/h]（目標領域の平均）
WIN = {"p1314": (13, 14), "p1317": (13, 17)}

cm.use_japanese_font()


def prec(hdir):
    """目標領域の平均降水強度 [mm/h]（10 分ごと、0 s〜）。"""
    acc, n = 0.0, 0
    for f in sorted(os.listdir(hdir)):
        with Dataset(f"{hdir}/{f}") as d:
            i, j = cm._ij(d)
            ii = np.flatnonzero((i >= I0) & (i < I0 + K))
            jj = np.flatnonzero((j >= J0) & (j < J0 + K))
            if not (ii.size and jj.size):
                continue
            a = np.asarray(d.variables["PREC"][:, jj[0]:jj[-1] + 1, ii[0]:ii[-1] + 1], dtype=np.float64)
        acc = acc + a.sum(axis=(1, 2))
        n += ii.size * jj.size
    if n != K * K:
        sys.exit(f"{hdir}: 目標領域の格子が {n} 個です。")
    return acc / n * 3600.0


def summary(p, t):
    hr = p[1:].reshape(-1, 6).mean(axis=1)           # 列 h = T0 + h 時〜
    k = np.flatnonzero(p > ONSET)
    out = {nm: hr[a - T0:b - T0].sum() for nm, (a, b) in WIN.items()}
    out["onset"] = t[k[0]] if k.size else np.nan
    return out


def main():
    figd = cm.figdir()
    z = np.load(f"{EXP}/control.npz")
    names = [str(s) for s in z["names"]]
    P = {nm: prec(f"{EXP}/hist/{k:04d}") for k, nm in enumerate(names, start=1)}
    P["orig"] = prec(ORIG)
    t = T0 + np.arange(len(P["none"])) * DT / 3600.0
    S = {nm: summary(p, t) for nm, p in P.items()}
    ref = S["none"]
    print(f"実験: {EXP}")
    print(f"{'':20s} {'13〜14 時':>9s} {'差':>7s} {'13〜17 時':>9s} {'差':>7s} {'降り始め':>8s} {'差[分]':>7s}  予測 ΔY")
    for nm in ["orig"] + names:
        s = S[nm]
        pred = f"{float(z['pred_' + nm]):+.3f}" if f"pred_{nm}" in z else ""
        print(f"{nm:20s} {s['p1314']:9.3f} {s['p1314'] - ref['p1314']:+7.3f} {s['p1317']:9.3f} {s['p1317'] - ref['p1317']:+7.3f}"
              f" {s['onset']:8.2f} {(s['onset'] - ref['onset']) * 60:+7.1f}  {pred}")
    print("（差は修正なしの流し直し none との差。orig は phase9_patch_t08 の mdet。none と orig の差がカオスの揺れの目安）")

    fig, axs = plt.subplots(2, 1, figsize=(11, 8), sharex=True, constrained_layout=True)
    for ax, tg in zip(axs, WIN):
        a, b = WIN[tg]
        ax.axvspan(a, b, color=cm.C3, alpha=0.08, lw=0)
        ax.plot(t, P["none"], color="k", lw=1.8, label="修正なし（流し直し）")
        ax.plot(t, P["orig"], color="0.5", lw=1.2, ls="--", label="修正なし（もとの mdet）")
        for nm, c in [(f"{tg}_full_clip", cm.C1), (f"{tg}_local_clip", cm.C2), (f"{tg}_full_noclip", cm.C1),
                      (f"{tg}_local_noclip", cm.C2), (f"{tg}_random", "0.3")]:
            ax.plot(t, P[nm], color=c, lw=1.0, ls=":" if "noclip" in nm else "-", label=nm)
        ax.set_ylabel("目標領域の降水強度 [mm/h]")
        ax.set_title(f"目標 {tg}（{a}〜{b} 時の雨）", loc="left", fontsize=10)
        ax.grid(alpha=0.3)
        ax.legend(frameon=False, fontsize=8, ncol=2, loc="upper left")
    axs[-1].set_xlabel("STIME からの時間 [h]（8 時に修正を足して 18 時まで予報）")
    axs[-1].set_xlim(T0, t[-1])
    fig.savefig(f"{figd}/control_target.png", dpi=110)
    print(f"図: {figd}/control_target.png")


if __name__ == "__main__":
    main()
