#!/usr/bin/env python3
"""7c の ①: 真値（mdet）がアンサンブルの中にいるかを、0 分と 60 分の history で調べる（Phase 7）。

- 各 member と mdet の距離 RMS(member − mdet)、各 member と平均の距離 RMS(member − mean)、
  平均と mdet の距離 RMS(mean − mdet)、ばらつき sqrt(mean(var)) を、全格子点で計算する。
- 真値がアンサンブルと同じ分布から来ていれば、RMS(member − mdet) は RMS(member − mean) と同じくらいになり、
  RMS(mean − mdet) はばらつきと同じくらいになる。

使い方: STIME=… OUTDIR=… python3 check_members.py
"""
import numpy as np

import common as cm
from common import rms

VARS = ["U", "T", "QV"]


def read(mem, t):
    return cm.read_hist(cm.hist_dir(mem), VARS, t)


def main():
    for t in [0.0, 3600.0]:
        M = [read(f"{m:04d}", t) for m in range(1, 21)]
        D = read("mdet", t)
        print(f"--- t = {t / 60:.0f} 分")
        for v in VARS:
            X = np.stack([m[v] for m in M])
            mean = X.mean(0)
            d = [rms(X[m] - D[v]) for m in range(20)]
            dm = [rms(X[m] - mean) for m in range(20)]
            sp = np.sqrt(np.mean(X.var(0, ddof=1)))
            print(f"{v}: RMS(member−mdet) m1..20 =", " ".join(f"{x:.3g}" for x in d))
            print("    RMS(member−mean)  m1..20 =", " ".join(f"{x:.3g}" for x in dm))
            print(f"    RMS(mean−mdet) {rms(mean - D[v]):.3g}  ばらつき {sp:.3g}  mdet に最も近い member {int(np.argmin(d)) + 1}")


if __name__ == "__main__":
    main()
