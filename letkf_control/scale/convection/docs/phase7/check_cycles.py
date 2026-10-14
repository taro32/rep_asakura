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

出力: 表（標準出力）と figs/cycles_timeseries.png（環境変数 FIGDIR で出力先を変えられる）
使い方: python3 check_cycles.py [--fast] [解析時刻の数（既定: あるだけ）]
"""
import glob
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from netCDF4 import Dataset

import check_letkf as cl
import check_truth as ct

STIME = os.environ.get("STIME", "20000101000000")   # Phase 7d: STIME=20000131000000
HERE = os.path.dirname(os.path.abspath(__file__))
FIGDIR = os.environ.get("FIGDIR", f"{HERE}/figs")
KEYS = ["U [m/s]", "V [m/s]", "W [m/s]", "T [K]", "P [hPa]", "QV [g/kg]", "QHYD [g/kg]"]


def tstr(k):
    """STIME + k 時間の時刻文字列。"""
    from datetime import datetime, timedelta
    t = datetime.strptime(STIME, "%Y%m%d%H%M%S") + timedelta(hours=k)
    return t.strftime("%Y%m%d%H%M%S")


def label(t):
    return f"init_{t[0:8]}-{t[8:14]}.000"


def read_restart(path, t):
    files = sorted(glob.glob(f"{path}/{label(t)}.pe*.nc"))
    assert len(files) == 144, f"{path}: {len(files)} files"
    out = {}
    for f in files:
        with Dataset(f) as d:
            i = np.rint(d.variables["x"][:] / cl.DX - 0.5).astype(int)
            j = np.rint(d.variables["y"][:] / cl.DX - 0.5).astype(int)
            for v in ct.VARS3:
                a = d.variables[v][:].transpose(2, 0, 1)
                if v not in out:
                    out[v] = np.full((a.shape[0], cl.NY, cl.NX), np.nan)
                out[v][:, j[:, None], i[None, :]] = a
    return out


def first(*paths):
    for p in paths:
        if os.path.isdir(p) and glob.glob(f"{p}/*.nc"):
            return p
    raise FileNotFoundError(paths)


def wind_sprd(tprev, t):
    """U, V, W のばらつき（格子の中心）。第一推定は tprev の hist/<member> の 3600 s、解析は t の anal/<member>。"""
    g = {k: np.empty((20, cl.NZ, cl.NY, cl.NX)) for k in ["U", "V", "W"]}
    a = {k: np.empty((20, cl.NZ, cl.NY, cl.NX)) for k in ["U", "V", "W"]}
    for m in range(20):
        mem = f"{m + 1:04d}"
        for f in sorted(glob.glob(f"{cl.OUTDIR}/{tprev}/hist/{mem}/history.pe*.nc")):
            with Dataset(f) as d:
                it = int(np.flatnonzero(np.isclose(d.variables["time"][:], 3600.0))[0])
                i = np.rint(d.variables["x"][:] / cl.DX - 0.5).astype(int)
                j = np.rint(d.variables["y"][:] / cl.DX - 0.5).astype(int)
                for k in g:
                    g[k][m][:, j[:, None], i[None, :]] = d.variables[k][it]
        p = ct.physical(read_restart(f"{cl.OUTDIR}/{t}/anal/{mem}", t))
        for k in a:
            a[k][m] = p[f"{k} [m/s]"]
    return ({f"{k} [m/s]": g[k].std(axis=0, ddof=1) for k in g},
            {f"{k} [m/s]": a[k].std(axis=0, ddof=1) for k in a})


def main():
    fast = "--fast" in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    ncyc = int(args[0]) if args else None
    rows = []
    k = 1
    while ncyc is None or k <= ncyc:
        t, tprev = tstr(k), tstr(k - 1)
        d = f"{cl.OUTDIR}/{t}"
        if not os.path.isdir(f"{d}/anal/mean"):
            break
        ptrue = first(f"{d}/gues/mdet", f"{d}/anal/mdet")
        pgues = first(f"{d}/gues_letkf/mean", f"{d}/gues/mean")
        T = ct.physical(read_restart(ptrue, t))
        G = ct.physical(read_restart(pgues, t))
        A = ct.physical(read_restart(f"{d}/anal/mean", t))
        SG = ct.physical_sprd(read_restart(first(f"{d}/gues_letkf/sprd", f"{d}/gues/sprd"), t))
        SA = ct.physical_sprd(read_restart(f"{d}/anal/sprd", t))
        if not fast:
            wg, wa = wind_sprd(tprev, t)
            SG.update(wg)
            SA.update(wa)
        else:
            for key in ["U [m/s]", "V [m/s]", "W [m/s]"]:
                SG[key] = SA[key] = np.full_like(T[key], np.nan)
        obscol = np.zeros((cl.NY, cl.NX), bool)       # check_truth.py と同じ: 観測の柱と、そこから最も遠い柱
        obscol[::ct.OBS_STEP, ::ct.OBS_STEP] = True
        mid = np.zeros((cl.NY, cl.NX), bool)
        mid[2::ct.OBS_STEP, 2::ct.OBS_STEP] = True
        r = {key: (cl.rms(G[key] - T[key]), cl.rms(A[key] - T[key]), cl.rms(SG[key]), cl.rms(SA[key]),
                   cl.rms((A[key] - T[key])[:, obscol]) / cl.rms((G[key] - T[key])[:, obscol]),
                   cl.rms((A[key] - T[key])[:, mid]) / cl.rms((G[key] - T[key])[:, mid])) for key in KEYS}
        rows.append((t, r))
        print(f"--- 解析時刻 {t}（cycle {k}）  真値: {os.path.relpath(ptrue, d)}  第一推定: {os.path.relpath(pgues, d)}")
        print(f"   {'変数':12s} {'RMSE 第一推定':>12s} {'RMSE 解析':>10s} {'解析/第一推定':>12s} {'ばらつき 第一推定':>14s} {'ばらつき 解析':>12s} {'RMSE/ばらつき':>12s} {'改善 観測の柱':>12s} {'改善 観測の間':>12s}")
        for key in KEYS:
            rg, ra, sg, sa, ro, rm = r[key]
            print(f"   {key:12s} {rg:12.4e} {ra:10.4e} {ra / rg:12.3f} {sg:14.4e} {sa:12.4e} {rg / sg:12.2f} {ro:12.3f} {rm:12.3f}")
        sys.stdout.flush()
        k += 1
    if not rows:
        sys.exit("解析時刻が見つかりません。")

    # のこぎり型の時系列: 各 cycle で 第一推定（t, 上） → 解析（t, 下）
    os.makedirs(FIGDIR, exist_ok=True)
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
