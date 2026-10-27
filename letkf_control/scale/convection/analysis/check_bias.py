#!/usr/bin/env python3
"""解析の誤差を「領域平均の偏り」と「偏りを除いた部分」に分ける（2026-10-17、B-1 で P の誤差が同化ありだけで増え続けたため）。

各時刻で、誤差 = 解析の平均 − 真値 の、全格子点の平均（偏り）、RMSE、偏りを除いた RMSE（標準偏差）を、P・T・U・QV について出す。
P は層ごとの領域平均の偏りも、最下層・中層・最上層で出す。
使い方: STIME=20000131000000 python3 check_bias.py <真値の場所> <実験名>=<結果の場所> ...
"""
import os
import sys

import numpy as np

import common as cm
from common import physical, tstr


def first(*paths):
    for p in paths:
        if os.path.isdir(p) and any(f.endswith(".nc") for f in os.listdir(p)):
            return p
    raise FileNotFoundError(paths)


def main():
    truth = sys.argv[1]
    exps = [a.split("=", 1) for a in sys.argv[2:]]
    keys = ["P [hPa]", "T [K]", "U [m/s]", "QV [g/kg]"]
    k = 1
    while all(os.path.isdir(f"{p}/{tstr(k)}/anal/mean") for _, p in exps):
        t = tstr(k)
        T = physical(cm.read_restart(first(f"{truth}/{t}/gues/mdet", f"{truth}/{t}/anal/mdet"), t))
        print(f"--- {t}（{k} 時間目）")
        for e, p in exps:
            A = physical(cm.read_restart(f"{p}/{t}/anal/mean", t))
            s = []
            for key in keys:
                d = A[key] - T[key]
                s.append(f"{key.split()[0]} 偏り {d.mean():+.4f} RMSE {np.sqrt((d ** 2).mean()):.4f} 偏りを除く {d.std():.4f}")
            dp = (A["P [hPa]"] - T["P [hPa]"]).mean(axis=(1, 2))
            s.append(f"P の層ごとの偏り（層 1・32・64）{dp[0]:+.4f} {dp[31]:+.4f} {dp[-1]:+.4f}")
            print(f"   {e:10s} " + " | ".join(s))
        sys.stdout.flush()
        k += 1


if __name__ == "__main__":
    main()
