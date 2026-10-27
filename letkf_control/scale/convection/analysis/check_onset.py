#!/usr/bin/env python3
"""7c の ①: member ごとに、対流がいつ始まったかを領域平均の QHYD（雲・降水の合計）の時間変化で比べる（Phase 7）。
step 7 の history（0–60 分、10 分ごと）を使う。

使い方: STIME=… OUTDIR=… python3 check_onset.py
"""
import glob

import numpy as np
from netCDF4 import Dataset

import common as cm


def series(mem):
    tot = None
    for f in sorted(glob.glob(f"{cm.hist_dir(mem)}/history.pe*.nc")):
        with Dataset(f) as d:
            q = np.asarray(d.variables["QHYD"][:], dtype=np.float64)     # (time, z, y, x)
            s = q.sum(axis=(1, 2, 3))
            t = np.asarray(d.variables["time"][:])
            tot = s if tot is None else tot + s
    return t, tot / (cm.NX * cm.NY * cm.NZ) * 1e3                      # 全格子点の平均 [g/kg]


def main():
    mems = [f"{m:04d}" for m in range(1, 21)] + ["mdet"]
    for mem in mems:
        t, s = series(mem)
        print(f"{mem}: " + " ".join(f"{x:.2e}" for x in s) + (f"   （t = {list((t / 60).astype(int))} 分）" if mem == "0001" else ""))


if __name__ == "__main__":
    main()
