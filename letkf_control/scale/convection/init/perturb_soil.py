#!/usr/bin/env python3
"""スピンアップ後の restart に土壌水分の摂動を入れ、20 member + mdet の初期値を作る（Phase 7d）。

浅倉さんの論文（2.1.3 摂動デザイン）に倣う:
- 大気は全 member で同じ（identical twin）。スピンアップの restart をそのまま使い、土壌水分だけを変える。
- 摂動は、地表面（最上層）の土壌水分に、一様分布 −a < x′ < a のホワイトノイズをパッチ単位で足す。
  論文の基準設定は a = 0.01（0.2 の約 5%）、パッチ 1.5 km。ここでは格子が 2 km なので、パッチは 1 格子（2 km）にする。
- member ごと（mdet = 21 番目を含む）に別の乱数の種を使う。真値（mdet）も member と同じ作り方で作る。
- 加えたあと、土壌水分を 0 以上、上限（裸地の STRGMAX = 0.5）以下に切り詰める（a = 0.01 ではまず起きない）。

出力: GEN/<m>/init_<STIME>.pe*.nc（m = 1–21）、GEN/md5.txt（import_rep_asakura.sh の MD5_LIST の形式）、
      GEN/perturbation.npz（各 member の摂動の場。切り詰め後の実際の差）
使い方: python3 perturb_soil.py   （設定は下の定数）

40 member に増やすとき（2026-10-15、Phase 7d の感度実験 M40）は、新しい member だけを作る:
  GEN=/work/gv42/v42013/20260923_enkc_convection/init_soil_m40 M_FIRST=21 M_LAST=40 SEED_SHIFT=1 python3 perturb_soil.py
  種は SEED + m + SEED_SHIFT（21〜40 番は SEED + 22〜41。元の mdet の種 SEED + 21 と重ならない）。
  この場合 md5.txt は md5_new.txt に書く（元の 1〜20・mdet と合わせた記録は init/make_m40.sh が作る）。
"""
import glob
import hashlib
import os
import shutil
import sys

import numpy as np
from netCDF4 import Dataset

SRC = "/work/gv42/v42013/20260923_enkc_convection/spinup_20261003/restart"
SRC_LABEL = "restart_20000131-000000.000"
GEN = os.environ.get("GEN", "/work/gv42/v42013/20260923_enkc_convection/init_soil_20261003")
LABEL = "init_20000131-000000.000"      # cycle が読む名前（STIME = 20000131000000）

AMP = 0.01          # 振幅 a [m3/m3]（論文の基準設定）
PATCH = 1           # パッチの大きさ [格子]（1 格子 = 2 km。論文の基準は 1.5 km）
LAYERS = [0]        # 摂動を入れる土壌の層（0 = 最上層、厚さ 5 cm）
WMAX = 0.5          # 土壌水分の上限（param.bucket.conf の Desert の STRGMAX。LANDUSE_AllLand は PFT 1）
NMEM = 21           # 1–20 = member、21 = mdet
SEED = 20261003     # member m の種は SEED + m（+ SEED_SHIFT）
M_FIRST = int(os.environ.get("M_FIRST", 1))      # 作る番号の範囲（既定 1〜NMEM）
M_LAST = int(os.environ.get("M_LAST", NMEM))
SEED_SHIFT = int(os.environ.get("SEED_SHIFT", 0))
MEMS = range(M_FIRST, M_LAST + 1)
MD5_NAME = "md5.txt" if (M_FIRST, M_LAST, SEED_SHIFT) == (1, NMEM, 0) else "md5_new.txt"
DX = 2000.0
NX = NY = 120
NPE = 144


def main():
    files = sorted(glob.glob(f"{SRC}/{SRC_LABEL}.pe*.nc"))
    if len(files) != NPE:
        sys.exit(f"{SRC} の {SRC_LABEL} が {len(files)} 個です（{NPE} 個必要）。")
    for m in MEMS:
        if glob.glob(f"{GEN}/{m}/*.nc"):
            sys.exit(f"{GEN}/{m} にすでにファイルがあります。上書きしないので止めます。")
    if NX % PATCH or NY % PATCH:
        sys.exit("PATCH は格子数の約数にしてください。")

    fields = {}
    for m in MEMS:
        rng = np.random.default_rng(SEED + m + SEED_SHIFT)
        small = rng.uniform(-AMP, AMP, size=(NY // PATCH, NX // PATCH))
        pert = np.kron(small, np.ones((PATCH, PATCH)))           # (NY, NX)
        d = f"{GEN}/{m}"
        os.makedirs(d, exist_ok=True)
        applied = np.zeros((len(LAYERS), NY, NX))
        for f in files:
            pe = f[f.rindex(".pe"):]                               # ".pe000000.nc"
            out = f"{d}/{LABEL}{pe}"
            shutil.copyfile(f, out)
            os.chmod(out, 0o640)
            with Dataset(out, "r+") as nc:
                i = np.rint(nc.variables["x"][:] / DX - 0.5).astype(int)
                j = np.rint(nc.variables["y"][:] / DX - 0.5).astype(int)
                w = nc.variables["LAND_WATER"]                     # (y, x, lz)
                a = np.array(w[:])
                for n, k in enumerate(LAYERS):
                    new = np.clip(a[:, :, k] + pert[np.ix_(j, i)], 0.0, WMAX)
                    applied[n][np.ix_(j, i)] = new - a[:, :, k]
                    a[:, :, k] = new
                w[:] = a
        fields[f"m{m}"] = applied
        print(f"member {m:2d}: 摂動 min {applied.min():+.5f} max {applied.max():+.5f} 標準偏差 {applied.std():.5f}")

    # md5 の記録（"<md5>  <m>/<file>" の形式。import_rep_asakura.sh の MD5_LIST に渡す）
    with open(f"{GEN}/{MD5_NAME}", "w") as fo:
        for m in MEMS:
            for f in sorted(glob.glob(f"{GEN}/{m}/{LABEL}.pe*.nc")):
                h = hashlib.md5(open(f, "rb").read()).hexdigest()
                fo.write(f"{h}  {m}/{os.path.basename(f)}\n")
                os.chmod(f, 0o440)
    np.savez_compressed(f"{GEN}/perturbation.npz", layers=np.array(LAYERS), amp=AMP, patch=PATCH, seed=SEED, seed_shift=SEED_SHIFT, **fields)
    shutil.copyfile(os.path.abspath(__file__), f"{GEN}/perturb_soil.py")
    print(f"完了: {GEN}（{MD5_NAME}, perturbation.npz）")


if __name__ == "__main__":
    main()
