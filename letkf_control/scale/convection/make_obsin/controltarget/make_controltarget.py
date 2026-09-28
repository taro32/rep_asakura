#!/usr/bin/env python3
"""LETKC の controltarget を作る（2 km 格子用）。

形式は case_tc の cntltargetmakein_p.f90 と同じ:
  Fortran sequential unformatted（リトルエンディアン）、1 レコードに real(4) が 8 個
    1: 要素番号   2: 経度   3: 緯度   4: 高さ [m]
    5: 目標値     6: 誤差   7: 観測の種類   8: 0.0
  地上気圧（要素番号 14593）の目標値・誤差の単位は hPa。

目標地点は領域中心の格子点（全体の格子番号 60, 60。1 始まり）。
経度・緯度・最下層の高さは、cycle が出力した history から読む。

地上気圧の目標では、LETKC はモデルの地上気圧（SFC_PRES）を「高さ」の項目の高さに換算してから目標と比べる
（common_letkc/common_obs_scale.f90 の prsadj。高さ 37.5 m なら約 4.3 hPa 低くなる）。
地形はないので、高さを 0 m にすれば換算されず、SFC_PRES とそのまま比べられる。

使い方:
  python3 make_controltarget.py nocontrol            # controltarget_nocontrol を作る
  python3 make_controltarget.py nocontrol --install  # さらに $OUTDIR/obs/controltarget に置く

  nocontrol: 地上気圧の目標値 10 hPa（制御なし）。
             LETKC は「目標値 − モデルの値」が負の目標を捨てるので、制御は一度もかからない。
  ctltest:   地上気圧の目標値 1000.03 hPa・誤差 0.01 hPa・高さ 0 m（M1b 1 回目。制御の計算が働くかを確かめる）。
  ctltest_lev1: 地上気圧の目標値 995.795 hPa・誤差 0.01 hPa・高さ最下層 37.5 m（M1b 2 回目。37.5 m に換算した値の平均 + 3.5 Pa）。
             目標地点の 60 分の地上気圧（M1a の予報）は mdet 999.978、20 member 平均 999.995、ばらつき 0.0115 hPa。
             目標は member 平均より +0.035、mdet より +0.05 hPa 高く、ばらつきの 3〜4 倍。
             指標として選んだ値ではない（計画書 Phase 6、8.1 節）。
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
    # 名前: (要素番号, 目標値, 誤差, 観測の種類, 高さ)
    #   高さ: "lev1" は最下層の高さ（history の z の 1 番目）、数値はその高さ [m]
    "nocontrol": (14593, 10.0, 1.0, 1.0, "lev1"),       # 地上気圧 10 hPa（ADPUPA）
    "ctltest":   (14593, 1000.03, 0.01, 1.0, 0.0),      # 地上気圧 1000.03 hPa（M1b 1 回目。目標がどの格子点でも使われなかった）
    # M1b 2 回目: 高さを case_tc と同じ最下層（37.5 m）に戻す。LETKC はモデルの地上気圧を 37.5 m に換算して比べるので、
    # 目標値も換算後の値で決める。60 分の目標地点の換算値は 20 member 平均 99576.03 Pa（ばらつき 1.26 Pa）、mdet 99574.35 Pa。
    # 目標は平均 + 約 3.5 Pa（mdet + 5.2 Pa）。
    "ctltest_lev1": (14593, 995.795, 0.01, 1.0, "lev1"),
    # スロットの確認（2026-09-27）: 同じ目標を 2 つ書き、8 番目の数値（時刻のずれ dif [s]。スロットの割り当てに使われる）だけを変える。
    #   dif = 0     → スロット 7（60 分）、dif = -3600 → スロット 1（0 分）
    # 値のリストを渡すと複数レコードを書く。6 番目の要素が dif（省略時 0）。
    "slotcheck": [(14593, 995.795, 0.01, 1.0, "lev1", 0.0),
                  (14593, 995.795, 0.01, 1.0, "lev1", -3600.0)],
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

    entries = TARGETS[a.name]
    if not isinstance(entries, list):
        entries = [entries]
    lon, lat, z1 = center_point()

    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, f"controltarget_{a.name}")
    with open(out, "wb") as f:
        for e in entries:
            elm, val, err, typ, hgt = e[:5]
            dif = e[5] if len(e) > 5 else 0.0
            z = z1 if hgt == "lev1" else float(hgt)
            wk = [float(elm), lon, lat, z, val, err, typ, dif]
            body = struct.pack("<8f", *wk)
            f.write(struct.pack("<i", len(body)) + body + struct.pack("<i", len(body)))
            print(f"{out}: elm={elm} lon={lon:.6f} lat={lat:.6f} z={z} val={val} err={err} typ={typ} dif={dif}")

    if a.install:
        dst = f"{OUTDIR}/obs/controltarget"
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(out, dst)
        print(f"置いた: {dst}")


if __name__ == "__main__":
    main()
