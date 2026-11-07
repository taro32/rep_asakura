#!/usr/bin/env python3
"""パッチ型の土壌水分の摂動を入れたアンサンブル予報の入力を作る（2026-11-03）。

Phase 8（result_m80）の T_INT 時の解析（80 member と mdet）から、同化なしで HOURS 時間予報する。
member にだけ、20 km 四方のパッチごとに一様乱数の土壌水分の摂動を足す（mdet には足さない＝真値はそのまま）。
- パッチ: PATCH × PATCH 格子（10 × 10 = 20 km 四方）。目標領域（格子 i 35〜44・j 55〜64、0 始まり）が 1 つのパッチに
  ちょうど入るよう、OFFSET 格子ずらす（二重周期なので、端のパッチは反対側につながる）
- 振幅: 一様分布 −A〜+A、A = SIGMA × √3（標準偏差 SIGMA）。member ごとに別の乱数の種
- 層: LAYERS（0 = 第 1 層 0〜5 cm、1 = 第 2 層 5〜20 cm）に同じ値を足す。足したあと 0〜WMAX に切り詰める
- 予報は letkf_control の scale-rm_ens（Phase 8 の cycle と同じ実行ファイル・同じ物理設定）で、81 本（0001〜0080 = member、
  0081 = mdet）を 1 つのジョブで流す。各 member の設定は Phase 8 の 8 時の設定（run_template_src.conf）から、
  時刻・入出力・期間・history の項目だけを変えたもの

作るもの（OUT = /work/gv42/v42013/20260923_enkc_convection/<NAME>）:
  OUT/init/<m>/init_<T_INT>.pe*.nc      初期値（member は摂動入り）
  OUT/work/<m>/run.d01_<T_INT>.conf     各 member の SCALE の設定
  OUT/work/launcher.conf                scale-rm_ens の起動用の設定
  OUT/perturbation.npz                  各 member の摂動の場（第 1 層、切り詰め後の実際の差）と設定
使い方: python3 make_patch_fcst.py [member 数（既定 80。試験用に少なくできる）]
"""
import glob
import os
import shutil
import sys

import numpy as np
from netCDF4 import Dataset

NAME = os.environ.get("NAME", "phase9_patch_t08")
BASE = "/work/gv42/v42013/20260923_enkc_convection"
SRC = f"{BASE}/result_m80"
OUT = f"{BASE}/{NAME}"
HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = f"{HERE}/run_template_src.conf"   # Phase 8 の member 0005・8 時の設定（tmp/convection から写したもの）

T_INT = os.environ.get("T_INT", "20000131080000")
HOURS = int(os.environ.get("HOURS", 10))       # 予報の長さ [h]
NMEM = int(sys.argv[1]) if len(sys.argv) > 1 else 80
PATCH = 10                                      # パッチの大きさ [格子]（20 km）
OFFSET = 5                                      # パッチの切れ目を目標領域に合わせるずらし [格子]（35 = 3 × 10 + 5）
SIGMA = float(os.environ.get("SIGMA", 0.02))    # 摂動の標準偏差 [m³/m³]
AMP = SIGMA * np.sqrt(3.0)                      # 一様分布の振幅
LAYERS = [0, 1]                                 # 摂動を入れる層（0〜20 cm）
WMAX = 0.5                                      # 土壌水分の上限（STRGMAX）
SEED = 20261103
NX = NY = 120
DX = 2000.0
LABEL = f"init_{T_INT[:8]}-{T_INT[8:]}.000"
HIST_ITEMS = ["PREC", "LHFLX", "SHFLX", "PBLH", "SFC_PRES", "U10m", "V10m", "T2", "Q2", "PW", "OLR",
              "LAND_WATER", "LAND_TEMP", "LAND_RUNOFF", "GHFLX",
              "U", "V", "W", "T", "QV", "PRES", "MSE"]


def patch_field(rng):
    """パッチごとに一様乱数の場（NY, NX）。格子 (j, i) は、パッチ ((j − OFFSET) // PATCH, (i − OFFSET) // PATCH) に属する。"""
    small = rng.uniform(-AMP, AMP, size=(NY // PATCH, NX // PATCH))
    jj = ((np.arange(NY) - OFFSET) % NY) // PATCH
    ii = ((np.arange(NX) - OFFSET) % NX) // PATCH
    return small[jj[:, None], ii[None, :]]


def make_init(m, src, pert):
    """src の restart を OUT/init/<m>/ に写し、pert（NY, NX。None なら足さない）を LAYERS に足す。実際の差（第 1 層）を返す。"""
    dst = f"{OUT}/init/{m}"
    os.makedirs(dst, exist_ok=True)
    files = sorted(glob.glob(f"{src}/{LABEL}.pe*.nc"))
    if len(files) != 144:
        sys.exit(f"{src}: ファイルが {len(files)} 個です。")
    diff = np.zeros((NY, NX))
    for f in files:
        g = f"{dst}/{os.path.basename(f)}"
        shutil.copyfile(f, g)
        if pert is None:
            continue
        with Dataset(g, "r+") as d:
            i = np.rint(d.variables["x"][:] / DX - 0.5).astype(int)
            j = np.rint(d.variables["y"][:] / DX - 0.5).astype(int)
            w = d.variables["LAND_WATER"][:]                  # (y, x, lz)
            p = pert[np.ix_(j, i)]
            new = w.copy()
            for l in LAYERS:
                new[:, :, l] = np.clip(w[:, :, l] + p, 0.0, WMAX)
            d.variables["LAND_WATER"][:] = new
            diff[np.ix_(j, i)] = new[:, :, 0] - w[:, :, 0]
    return diff


def make_conf(m):
    """OUT/work/<m>/run.d01_<T_INT>.conf を作る。"""
    lines = open(TEMPLATE).read().splitlines()
    out = []
    for ln in lines:
        s = ln.strip()
        if s.startswith("&HISTORY_ITEM"):
            continue
        if s.startswith("IO_LOG_BASENAME"):
            ln = f'IO_LOG_BASENAME = "{OUT}/log/{m}_LOG",'
        elif s.startswith("TIME_DURATION ="):
            ln = f"TIME_DURATION = {HOURS * 3600}.D0,"
        elif s.startswith("RESTART_IN_BASENAME"):
            ln = f'RESTART_IN_BASENAME = "{OUT}/init/{m}/init",'
        elif s.startswith("RESTART_OUT_BASENAME"):
            ln = f'RESTART_OUT_BASENAME = "{OUT}/restart/{m}/init",'
        elif s.startswith("FILE_HISTORY_DEFAULT_BASENAME"):
            ln = f'FILE_HISTORY_DEFAULT_BASENAME = "{OUT}/hist/{m}/history",'
        elif s.startswith("MONITOR_OUT_BASENAME"):
            ln = f'MONITOR_OUT_BASENAME = "{OUT}/log/{m}.monitor",'
        out.append(ln)
    out += [f"&HISTORY_ITEM name='{v}' /" for v in HIST_ITEMS]
    text = "\n".join(out) + "\n"
    for key in ["result_m80"]:
        if key in text:
            sys.exit(f"設定に Phase 8 のパスが残っています: {key}")
    if T_INT != "20000131080000":
        sys.exit("TIME_STARTDATE の書き換えは未対応（T_INT は 8 時だけ）。")
    os.makedirs(f"{OUT}/work/{m}", exist_ok=True)
    for sub in ["log", f"restart/{m}", f"hist/{m}"]:
        os.makedirs(f"{OUT}/{sub}", exist_ok=True)
    with open(f"{OUT}/work/{m}/run.d01_{T_INT}.conf", "w") as f:
        f.write(text)


def main():
    if os.path.exists(f"{OUT}/init"):
        sys.exit(f"{OUT}/init がすでにあります（作り直すときは消す）。")
    mems = [f"{k:04d}" for k in range(1, NMEM + 1)]
    det = f"{NMEM + 1:04d}"                           # mdet は最後の番号に置く
    fields = {}
    for k, m in enumerate(mems, start=1):
        rng = np.random.default_rng(SEED + k)
        fields[m] = make_init(m, f"{SRC}/{T_INT}/anal/{m}", patch_field(rng))
        make_conf(m)
        print(f"{m}: 摂動（第 1 層、実際の差）min {fields[m].min():+.4f} max {fields[m].max():+.4f} 標準偏差 {fields[m].std():.4f}"
              f"  目標領域 {fields[m][55:65, 35:45].mean():+.4f}", flush=True)
    make_init(det, f"{SRC}/{T_INT}/anal/mdet", None)
    make_conf(det)
    print(f"{det}: mdet（摂動なし）")
    with open(f"{OUT}/work/launcher.conf", "w") as f:
        f.write(f"""&PARAM_ENSEMBLE
MEMBER = {NMEM + 1},
MEMBER_RUN = {NMEM + 1},
CONF_FILES = "<member>/run.d<domain>_{T_INT}.conf",
CONF_FILES_SEQNUM = .false.,
DET_RUN = .false.,
EFSO_RUN = .false.,
/

&PARAM_PROCESS
PPN = 4,
MEM_NODES = 36,
NUM_DOMAIN = 1,
PRC_DOMAINS = 144,
/
""")
    np.savez_compressed(f"{OUT}/perturbation.npz", sigma=SIGMA, amp=AMP, patch=PATCH, offset=OFFSET, layers=np.array(LAYERS),
                        seed=SEED, t_int=T_INT, mdet=det, **fields)
    print(f"作った: {OUT}（member {NMEM}、mdet = {det}）")


if __name__ == "__main__":
    main()
