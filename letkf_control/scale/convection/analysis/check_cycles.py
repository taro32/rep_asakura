#!/usr/bin/env python3
"""7c の ④: 制御なしで複数 cycle 回したとき、cycle ごとに解析が真値（mdet）に近づき続けるかを調べる（Phase 7）。

各 cycle の解析時刻 t（STIME + 1h, + 2h, …）で、全格子点について check_truth.py と同じ量を計算する。
- 真値: <t>/gues/mdet（LETKC が書き換える前の mdet。t で制御があっても、観測を作ったのはこちら）。
  最後の時刻には LETKC が走らないので <t>/anal/mdet。
- 第一推定の平均・ばらつき: <t>/gues_letkf/{mean,sprd}（次の cycle の LETKC の前に cycle.sh が退避したもの）。
  最後の時刻は <t>/gues/{mean,sprd}（上書きされていない）。
- 解析の平均・ばらつき: <t>/anal/{mean,sprd}。
- ばらつき: T, P, QV, 雲・降水は sprd（check_truth.physical_sprd の読み替え）。
  U, V, W は member から直接（第一推定は前の時刻の hist/<member> の 60 分、解析は anal/<member>）。--fast で U, V, W のばらつきを省く。

出力: 表（標準出力）と FIGDIR/cycles_timeseries.png
使い方: STIME=… OUTDIR=… FIGDIR=… python3 check_cycles.py [--fast] [解析時刻の数（既定: あるだけ）]
"""
import glob
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import common as cm
from common import physical, physical_sprd, rms, tstr

KEYS = ["U [m/s]", "V [m/s]", "W [m/s]", "T [K]", "P [hPa]", "QV [g/kg]", "QHYD [g/kg]"]


def first(*paths):
    for p in paths:
        if os.path.isdir(p) and glob.glob(f"{p}/*.nc"):
            return p
    raise FileNotFoundError(paths)


def main():
    fast = "--fast" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    ncyc = int(args[0]) if args else None
    rows = []
    k = 1
    while ncyc is None or k <= ncyc:
        t = tstr(k)                                  # 1 時間ごとの解析時刻で評価する（LCYCLE が 1 時間でなくても）
        tprev = cm.tprev_of(t)
        d = f"{cm.OUTDIR}/{t}"
        if not os.path.isdir(f"{d}/anal/mean"):
            break
        dt = f"{cm.TRUTHDIR}/{t}"                    # 真値の場所（感度実験は基準の結果）
        ptrue = first(f"{dt}/gues/mdet", f"{dt}/anal/mdet")
        pgues = first(f"{d}/gues_letkf/mean", f"{d}/gues/mean")
        T = physical(cm.read_restart(ptrue, t))
        G = physical(cm.read_restart(pgues, t))
        A = physical(cm.read_restart(f"{d}/anal/mean", t))
        SG = physical_sprd(cm.read_restart(first(f"{d}/gues_letkf/sprd", f"{d}/gues/sprd"), t))
        SA = physical_sprd(cm.read_restart(f"{d}/anal/sprd", t))
        if not fast:
            wg, wa = cm.wind_sprd(tprev, t)
            SG.update(wg)
            SA.update(wa)
        else:
            for key in ["U [m/s]", "V [m/s]", "W [m/s]"]:
                SG[key] = SA[key] = np.full_like(T[key], np.nan)
        obscol, mid = cm.obs_columns()                 # check_truth.py と同じ: 観測の柱と、そこから最も遠い柱
        r = {key: (rms(G[key] - T[key]), rms(A[key] - T[key]), rms(SG[key]), rms(SA[key]),
                   rms((A[key] - T[key])[:, obscol]) / rms((G[key] - T[key])[:, obscol]),
                   rms((A[key] - T[key])[:, mid]) / rms((G[key] - T[key])[:, mid])) for key in KEYS}
        rows.append((t, r))
        print(f"--- 解析時刻 {t}（cycle {k}）  真値: {ptrue}  第一推定: {os.path.relpath(pgues, d)}")
        print(f"   {'変数':12s} {'RMSE 第一推定':>12s} {'RMSE 解析':>10s} {'解析/第一推定':>12s} {'ばらつき 第一推定':>14s} {'ばらつき 解析':>12s} {'RMSE/ばらつき':>12s} {'改善 観測の柱':>12s} {'改善 観測の間':>12s}")
        for key in KEYS:
            rg, ra, sg, sa, ro, rm = r[key]
            print(f"   {key:12s} {rg:12.4e} {ra:10.4e} {ra / rg:12.3f} {sg:14.4e} {sa:12.4e} {rg / sg:12.2f} {ro:12.3f} {rm:12.3f}")
        sys.stdout.flush()
        k += 1
    if not rows:
        sys.exit("解析時刻が見つかりません。")

    # のこぎり型の時系列: 各 cycle で 第一推定（t, 上） → 解析（t, 下）
    FIGDIR = cm.figdir()
    fig, axs = plt.subplots(2, 4, figsize=(18, 8))
    hrs = np.arange(1, len(rows) + 1)
    for ax, key in zip(axs.ravel(), KEYS):
        x, y, s = [], [], []
        for h, (t, r) in zip(hrs, rows):
            x += [h, h]
            y += [r[key][0], r[key][1]]
            s += [r[key][2], r[key][3]]
        ax.plot(x, y, "-o", color="#1c2733", ms=4, label="RMSE (first guess → analysis)")
        ax.plot(x, s, "--", color="#c2410c", label="spread")
        ax.set_title(key)
        ax.set_xlabel("analysis time [h]")
        ax.set_ylim(bottom=0)
        ax.grid(alpha=0.3)
    axs[0, 0].legend(fontsize=9)
    axs.ravel()[-1].axis("off")
    fig.suptitle("Cycling without control: domain RMSE vs truth (mdet) and ensemble spread", fontsize=13)
    fig.tight_layout()
    fig.savefig(f"{FIGDIR}/cycles_timeseries.png", dpi=110)
    print(f"\n図: {FIGDIR}/cycles_timeseries.png")


if __name__ == "__main__":
    main()
