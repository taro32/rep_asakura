#!/usr/bin/env python3
"""obsmake に渡す観測地点の一覧（OBSIN）を作る（2 km 格子用、Phase 7）。

形式は case_tc の obsmakein_p.f90 と同じ:
  Fortran sequential unformatted（リトルエンディアン）、1 レコードに real(4) が 8 個
    1: 要素番号   2: 経度   3: 緯度   4: 気圧 [hPa]
    5: 観測値（仮の値。obsmake が mdet の予報から計算して上書きする）
    6: 誤差（obsmake が config.nml.obsmake の OBSERR_* で上書きする）
    7: 観測の種類（1.0 = ADPUPA）   8: 時刻のずれ dif [s]（0 → 60 分。スロット 7）

観測地点（2026-09-27 決定、計画書 Phase 7）:
  要素     U, V, T（2819, 2820, 3073）
  水平     4 格子おき（8 km）。全体の格子番号 1, 5, …, 117（1 始まり）の 30 × 30 点
  鉛直     2 層おき。モデルの層 1, 3, …, 63 の 32 層。気圧はその格子点・その層の 0 分の気圧
  → 30 × 30 × 32 × 3 = 86,400 個

経度・緯度・気圧は、cycle が出力した STIME の mdet の history（0 分）から読む。

使い方:
  python3 make_obsin.py            # obsin_uvt_intv4 を作る
  python3 make_obsin.py --check    # 作ったファイルを読み戻して要約を出す
"""
import argparse
import glob
import os
import struct
import sys

import numpy as np
from netCDF4 import Dataset

OUTDIR = "/work/gv42/v42013/20260923_enkc_convection/result"
HIST = f"{OUTDIR}/20000101000000/hist/mdet"      # 格子の経度・緯度・気圧を読む history
DX = 2000.0
NX = NY = 120
NZ = 64

ELMS = [2819, 2820, 3073]                         # U, V, T
ERR = 1.0                                         # 仮の値（obsmake が OBSERR_* で上書きする）
INTV_X = INTV_Y = 4
INTV_Z = 2
NAME = "obsin_uvt_intv4"


def read_global():
    """144 個の history から、全体の lon, lat（NY, NX）と 0 分の PRES（NZ, NY, NX）を組み立てる。"""
    lon = np.full((NY, NX), np.nan)
    lat = np.full((NY, NX), np.nan)
    pres = np.full((NZ, NY, NX), np.nan)
    files = sorted(glob.glob(f"{HIST}/history.pe*.nc"))
    if not files:
        sys.exit(f"history が {HIST} に見つかりません。")
    for f in files:
        with Dataset(f) as d:
            if d.variables["time"][0] != 0.0:
                sys.exit(f"{f}: 最初の時刻が 0 ではありません。")
            i = np.rint(d.variables["x"][:] / DX - 0.5).astype(int)
            j = np.rint(d.variables["y"][:] / DX - 0.5).astype(int)
            lon[np.ix_(j, i)] = d.variables["lon"][:]
            lat[np.ix_(j, i)] = d.variables["lat"][:]
            pres[:, j[:, None], i[None, :]] = d.variables["PRES"][0]
    if np.isnan(lon).any() or np.isnan(pres).any():
        sys.exit("history から埋まらない格子点があります。")
    return lon, lat, pres


def write(path):
    lon, lat, pres = read_global()
    n = 0
    with open(path, "wb") as f:
        for i in range(0, NX, INTV_X):
            for j in range(0, NY, INTV_Y):
                for k in range(0, NZ, INTV_Z):
                    for elm in ELMS:
                        wk = [float(elm), lon[j, i], lat[j, i], pres[k, j, i] * 0.01,
                              10.0, ERR, 1.0, 0.0]
                        body = struct.pack("<8f", *wk)
                        f.write(struct.pack("<i", len(body)) + body + struct.pack("<i", len(body)))
                        n += 1
    print(f"{path}: {n} 個")


def check(path):
    raw = np.fromfile(path, dtype="<i4").reshape(-1, 10)
    if not (np.all(raw[:, 0] == 32) and np.all(raw[:, 9] == 32)):
        sys.exit("レコード長が 32 バイトでないレコードがあります。")
    wk = raw[:, 1:9].copy().view("<f4")
    print(f"{path}: {len(wk)} 個")
    for e in np.unique(wk[:, 0]):
        print(f"  要素 {int(e)}: {np.sum(wk[:, 0] == e)} 個")
    for c, name in [(1, "経度"), (2, "緯度"), (3, "気圧 [hPa]"), (4, "観測値"), (5, "誤差"), (6, "種類"), (7, "dif [s]")]:
        print(f"  {name}: {wk[:, c].min():.6g} 〜 {wk[:, c].max():.6g}（異なる値 {len(np.unique(wk[:, c]))} 個）")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--check", action="store_true", help="作ったファイルを読み戻して要約を出す")
    a = p.parse_args()
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), NAME)
    if not a.check:
        write(path)
    check(path)


if __name__ == "__main__":
    main()
