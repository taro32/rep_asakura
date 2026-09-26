#!/usr/bin/env python3
"""LETKC の controltarget を作る（2 km 格子用）。

形式は case_tc の cntltargetmakein_p.f90 と同じ:
  Fortran sequential unformatted（リトルエンディアン）、1 レコードに real(4) が 8 個
    1: 要素番号   2: 経度   3: 緯度   4: 高さ [m]
    5: 目標値     6: 誤差   7: 観測の種類   8: 0.0
  地上気圧（要素番号 14593）の目標値・誤差の単位は hPa。

目標地点は領域中心の格子点（全体の格子番号 60, 60。1 始まり）。
経度・緯度・最下層の高さは、cycle が出力した history から読む。

使い方:
  python3 make_controltarget.py nocontrol            # controltarget_nocontrol を作る
  python3 make_controltarget.py nocontrol --install  # さらに $OUTDIR/obs/controltarget に置く

  nocontrol: 地上気圧の目標値 10 hPa（制御なし）。
             LETKC は「目標値 − モデルの値」が負の目標を捨てるので、制御は一度もかからない。
"""
import argparse
import glob
import os
import shutil
import struct
import sys

from netCDF4 import Dataset

OUTDIR = "/work/gv42/v42013/20260923_enkc_convection/result"
HIST = f"{OUTDIR}/20000101000000/hist/mdet"      # 格子の経度・緯度を読む history
DX = 2000.0
IG = JG = 60                                      # 目標地点の全体の格子番号（1 始まり）

TARGETS = {
    # 名前: (要素番号, 目標値, 誤差, 観測の種類)
    "nocontrol": (14593, 10.0, 1.0, 1.0),         # 地上気圧 10 hPa（ADPUPA）
}


def center_point():
    xc = (IG - 0.5) * DX
    yc = (JG - 0.5) * DX
    for f in sorted(glob.glob(f"{HIST}/history.pe*.nc")):
        with Dataset(f) as d:
            x = list(d.variables["x"][:])
            y = list(d.variables["y"][:])
            if xc in x and yc in y:
                i, j = x.index(xc), y.index(yc)
                return (float(d.variables["lon"][j, i]), float(d.variables["lat"][j, i]),
                        float(d.variables["z"][0]))
    sys.exit(f"格子点 ({IG}, {JG}) を含む history が {HIST} に見つかりません。")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("name", choices=TARGETS.keys())
    p.add_argument("--install", action="store_true", help="$OUTDIR/obs/controltarget に置く")
    a = p.parse_args()

    elm, val, err, typ = TARGETS[a.name]
    lon, lat, z1 = center_point()
    wk = [float(elm), lon, lat, z1, val, err, typ, 0.0]
    body = struct.pack("<8f", *wk)
    rec = struct.pack("<i", len(body)) + body + struct.pack("<i", len(body))

    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, f"controltarget_{a.name}")
    with open(out, "wb") as f:
        f.write(rec)
    print(f"{out}: elm={elm} lon={lon:.6f} lat={lat:.6f} z={z1} val={val} err={err} typ={typ}")

    if a.install:
        dst = f"{OUTDIR}/obs/controltarget"
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(out, dst)
        print(f"置いた: {dst}")


if __name__ == "__main__":
    main()
