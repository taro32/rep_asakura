#!/usr/bin/env python3
"""convection の解析スクリプトの共通部品（2026-10-14、docs/phase7・phase7d のスクリプトから切り出した）。

- 実験の場所と時刻: 環境変数 OUTDIR（結果の場所）・STIME（1 cycle 目の開始時刻）
- 格子・観測の定数
- 読み込み: 144 プロセスに分かれた history・restart を (NZ, NY, NX) に組み立てる。観測ファイル（obsmake の出力・OBSIN）
- 観測演算子: 経度・緯度がいちばん近い格子点の柱を取り、log p で鉛直に線形内挿する
  （7a で、obsmake の観測との差の標準偏差が観測誤差 0.100 になることを確認。docs/phase7/phase7_notes.md）
- restart の予報変数から物理量（U, V, W, T, P, QV, 雲・降水）への変換、LETKF の sprd の読み替え
- 図の日本語フォントと色
"""
import glob
import os
import sys
from datetime import datetime, timedelta

import numpy as np
from netCDF4 import Dataset

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.normpath(f"{HERE}/../docs")

# 結果の場所。退避した結果を読むときは変える（例: result/bak_soil_1cycle_9829615）
OUTDIR = os.environ.get("OUTDIR", "/work/gv42/v42013/20260923_enkc_convection/result")
# 1 cycle 目の開始時刻（Phase 7d の土壌水分摂動の初期値は STIME=20000131000000）
T0 = os.environ.get("STIME", "20000101000000")
# 真値（mdet）と観測の場所。感度実験（sens/）では基準の結果（result/）を指定する（既定は OUTDIR）
TRUTHDIR = os.environ.get("TRUTHDIR", OUTDIR)

DX = 2000.0
NX = NY = 120
NZ = 64
LCYCLE = int(os.environ.get("LCYCLE", 3600))       # 同化の間隔 [s]（感度実験 T30・T15 は 1800・900）
T_OBS = float(LCYCLE)                              # 観測の時刻（予報の終わり = 同化の間隔）
ELMS = {2819: "U", 2820: "V", 3073: "T"}           # 観測の要素番号
OBSERR = 0.1                                       # 観測誤差（U, V, T 共通）
GROSS = 5.0 * OBSERR                               # LETKF の QC（GROSS_ERROR × 観測誤差）
OBS_STEP = 4                                       # OBSIN の水平の間隔（格子番号 1, 5, …, 117）
OBSIN = os.path.normpath(f"{HERE}/../make_obsin/obsin/obsin_uvt_intv4")
VARS3 = ["DENS", "MOMX", "MOMY", "MOMZ", "RHOT", "QV", "QC", "QR", "QI", "QS", "QG"]


def tstr(k, t0=T0):
    """t0 + k 時間の時刻文字列。"""
    return (datetime.strptime(t0, "%Y%m%d%H%M%S") + timedelta(hours=k)).strftime("%Y%m%d%H%M%S")


def tprev_of(t):
    """解析時刻 t の第一推定を作った予報の開始時刻（t − LCYCLE）。"""
    return (datetime.strptime(t, "%Y%m%d%H%M%S") - timedelta(seconds=LCYCLE)).strftime("%Y%m%d%H%M%S")


def label(t):
    """restart のファイル名の時刻の部分。"""
    return f"init_{t[0:8]}-{t[8:14]}.000"


T1 = tstr(1)                                       # 1 cycle 目の解析時刻
OBS = f"{OUTDIR}/obs/obs_{T1}.dat"                 # 1 cycle 目の観測


def hist_dir(mem, t0=T0, base=None):
    """t0 に始めた予報の history（<OUTDIR>/<t0>/hist/<mem>。base を与えればその下）。"""
    return f"{base or OUTDIR}/{t0}/hist/{mem}"


def restart_dir(kind, mem, t=T1):
    """時刻 t の restart（<OUTDIR>/<t>/<kind>/<mem>。kind は gues・anal・gues_letkf）。"""
    return f"{OUTDIR}/{t}/{kind}/{mem}"


def _ij(d):
    """1 プロセス分のファイルの格子番号（0 始まり）。"""
    i = np.rint(d.variables["x"][:] / DX - 0.5).astype(int)
    j = np.rint(d.variables["y"][:] / DX - 0.5).astype(int)
    return i, j


# ---------------------------------------------------------------- 読み込み

def read_obs(path):
    """obsmake の出力・OBSIN を (観測数, 8) で読む。列は 要素, 経度, 緯度, 気圧 [hPa], 値, 誤差, 種類, 時刻差。"""
    raw = np.fromfile(path, dtype="<i4").reshape(-1, 10)
    if not (np.all(raw[:, 0] == 32) and np.all(raw[:, 9] == 32)):
        sys.exit(f"{path}: レコード長が 32 バイトでないレコードがあります。")
    return raw[:, 1:9].copy().view("<f4").astype(np.float64)


def read_obsdep(path):
    """LETKF の obsdep（QC を通った観測だけ）を (観測数, 12) で読む。列は 要素, 経度, 緯度, 気圧 [hPa], 値, 誤差, 種類, 時刻差,
    qc, O−B, O−A, 第一推定のばらつき（common/common_obs_scale.f90 の write_obs_dep。O−B・O−A は平均の状態に H を当てた値、
    ばらつきは member の H の標準偏差で、inflation の前）。"""
    raw = np.fromfile(path, dtype="<i4").reshape(-1, 14)
    if not (np.all(raw[:, 0] == 48) and np.all(raw[:, 13] == 48)):
        sys.exit(f"{path}: レコード長が 48 バイトでないレコードがあります。")
    return raw[:, 1:13].copy().view("<f4").astype(np.float64)


def read_hist(path, names, t=T_OBS, dtype=np.float64):
    """path の history から、時刻 t [s] の names を (..., NY, NX) で組み立てる。t = None なら全時刻（time が先頭の軸）。"""
    files = sorted(glob.glob(f"{path}/history.pe*.nc"))
    if not files:
        sys.exit(f"history が {path} に見つかりません。")
    out = {}
    for f in files:
        with Dataset(f) as d:
            i, j = _ij(d)
            for v in names:
                if t is None:
                    a = d.variables[v][:]
                else:
                    it = int(np.flatnonzero(np.isclose(d.variables["time"][:], t))[0])
                    a = d.variables[v][it]
                if v not in out:
                    out[v] = np.full(a.shape[:-2] + (NY, NX), np.nan, dtype=dtype)
                out[v][..., j[:, None], i[None, :]] = a
    return out


def hist_time(path):
    """path の history の時刻 [s]。"""
    with Dataset(sorted(glob.glob(f"{path}/history.pe*.nc"))[0]) as d:
        return np.asarray(d.variables["time"][:])


def read_global(path):
    """観測演算子のための lon, lat（NY, NX）と、60 分の U, V, T, PRES（NZ, NY, NX）。欠けがあれば止める。"""
    lon = np.full((NY, NX), np.nan)
    lat = np.full((NY, NX), np.nan)
    var = {v: np.full((NZ, NY, NX), np.nan) for v in ["U", "V", "T", "PRES"]}
    files = sorted(glob.glob(f"{path}/history.pe*.nc"))
    if not files:
        sys.exit(f"history が {path} に見つかりません。")
    for f in files:
        with Dataset(f) as d:
            t = np.asarray(d.variables["time"][:])
            it = np.flatnonzero(np.isclose(t, T_OBS))
            if len(it) != 1:
                sys.exit(f"{f}: 時刻 {T_OBS} s がありません（time = {t}）。")
            i, j = _ij(d)
            lon[np.ix_(j, i)] = d.variables["lon"][:]
            lat[np.ix_(j, i)] = d.variables["lat"][:]
            for v in var:
                var[v][:, j[:, None], i[None, :]] = d.variables[v][it[0]]
    if np.isnan(lon).any() or any(np.isnan(a).any() for a in var.values()):
        sys.exit("history から埋まらない格子点があります。")
    return lon, lat, var


def read_restart(path, t=T1, names=VARS3, with_z=False):
    """path の restart（時刻 t）から names を (層, NY, NX) で組み立てる。MOMZ は zh の 65 層のまま。"""
    files = sorted(glob.glob(f"{path}/{label(t)}.pe*.nc"))
    if len(files) != 144:
        sys.exit(f"{path}: ファイルが {len(files)} 個です。")
    out = {}
    for f in files:
        with Dataset(f) as d:
            i, j = _ij(d)
            for v in names:
                a = d.variables[v][:].transpose(2, 0, 1)
                if v not in out:
                    out[v] = np.full((a.shape[0], NY, NX), np.nan)
                out[v][:, j[:, None], i[None, :]] = a
            z = np.asarray(d.variables["z"][:])
    return (out, z) if with_z else out


# ---------------------------------------------------------------- 観測演算子

def nearest_column(lon, lat, olon, olat):
    """観測ごとに、経度・緯度がいちばん近い格子点の (j, i) と距離 [度] を返す。"""
    glon, glat = lon.ravel(), lat.ravel()
    jj = np.empty(len(olon), int)
    ii = np.empty(len(olon), int)
    dist = np.empty(len(olon))
    keys, inv = np.unique(np.stack([olon, olat], 1), axis=0, return_inverse=True)
    for n, (x, y) in enumerate(keys):
        d = np.hypot(glon - x, glat - y)
        m = np.argmin(d)
        sel = inv.ravel() == n
        jj[sel], ii[sel] = divmod(m, NX)
        dist[sel] = d[m]
    return jj, ii, dist


def interp_logp(prof, pres, p):
    """1 本の柱で log p について線形内挿する。範囲外は nan。"""
    lp = np.log(pres)[::-1]                        # 上ほど気圧が小さいので昇順に並べ替える
    return np.interp(np.log(p), lp, prof[::-1], left=np.nan, right=np.nan)


def obs_operator(field, pres, obs, jj, ii, sel):
    """観測 sel（番号の配列）の位置での field の値。鉛直の内挿には pres [Pa] を使う。"""
    return np.array([interp_logp(field[:, jj[n], ii[n]], pres[:, jj[n], ii[n]], obs[n, 3] * 100.0) for n in sel])


# ---------------------------------------------------------------- 物理量

# SCALE の定数（scale_const）
RDRY, RVAP, CVDRY, CVVAP, CL, CI, P00 = 287.04, 461.46, 717.60, 1384.14, 4218.0, 2106.0, 1.0e5


def center(r, dens):
    """MOMX（x の面）・MOMY（y の面）を格子の中心へ平均し（二重周期）、dens で割って U, V にする。"""
    u = 0.5 * (r["MOMX"] + np.roll(r["MOMX"], 1, axis=2)) / dens
    v = 0.5 * (r["MOMY"] + np.roll(r["MOMY"], 1, axis=1)) / dens
    return u, v


def temp_pres(r):
    """restart の DENS, RHOT, 水物質から、湿潤の気体定数・比熱で T [K]・P [Pa] を出す（SCALE と同じ式）。"""
    ql = r["QC"] + r["QR"]
    qi = r["QI"] + r["QS"] + r["QG"]
    qd = 1.0 - r["QV"] - ql - qi
    rtot = RDRY * qd + RVAP * r["QV"]
    cvtot = CVDRY * qd + CVVAP * r["QV"] + CL * ql + CI * qi
    p = P00 * (r["RHOT"] * rtot / P00) ** ((cvtot + rtot) / cvtot)
    return p / (r["DENS"] * rtot), p


def physical(r):
    """restart（mean・mdet・member）の予報変数を、LETKF の状態変数（U, V, W, T, P, QV）と雲・降水の合計に直す。"""
    u, v = center(r, r["DENS"])
    w = 0.5 * (r["MOMZ"][:-1] + r["MOMZ"][1:]) / r["DENS"]
    t, p = temp_pres(r)
    return {
        "U [m/s]": u, "V [m/s]": v, "W [m/s]": w, "T [K]": t, "P [hPa]": p * 1e-2,
        "QV [g/kg]": r["QV"] * 1e3,
        "QHYD [g/kg]": (r["QC"] + r["QR"] + r["QI"] + r["QS"] + r["QG"]) * 1e3,
    }


def physical_sprd(s):
    """sprd の restart を読み替える。LETKF は U, V, W, T, P のばらつきを、変換せずに restart の欄へ順に書く
    （common/common_mpi_scale.f90 の write_enssprd、「do not transform the spread output」）。
    欄との対応は、anal の 20 member から計算したばらつきと一致することで確認した（相関 0.99999 以上）:
      DENS ← U、MOMX ← V、MOMY ← W、MOMZ の 2〜65 層目 ← T、RHOT ← P。水物質は同じ名前の欄。"""
    return {
        "U [m/s]": s["DENS"], "V [m/s]": s["MOMX"], "W [m/s]": s["MOMY"],
        "T [K]": s["MOMZ"][1:], "P [hPa]": s["RHOT"] * 1e-2,
        "QV [g/kg]": s["QV"] * 1e3,
        "QHYD [g/kg]": np.sqrt(sum(s[q] ** 2 for q in ["QC", "QR", "QI", "QS", "QG"])) * 1e3,   # 各成分のばらつきの二乗和（相関は無視）
    }


def wind_sprd(tprev=T0, t=T1):
    """U, V, W のばらつきを member から直接計算する（格子の中心の値。誤差と同じ定義にそろえる）。
    LETKF の sprd の U, V, W は格子の面などの値で、中心へ平均した値より 1.5 倍ほど大きく出るので使わない。
    第一推定: tprev に始めた各 member の予報の 60 分の history（U, V, W は格子の中心の値）。
    解析: 時刻 t の anal/0001–0020 の restart を physical と同じ式で中心へ直す。"""
    g = {k: np.empty((20, NZ, NY, NX)) for k in ["U", "V", "W"]}
    a = {k: np.empty((20, NZ, NY, NX)) for k in ["U", "V", "W"]}
    for m in range(20):
        mem = f"{m + 1:04d}"
        h = read_hist(hist_dir(mem, tprev), ["U", "V", "W"])
        p = physical(read_restart(restart_dir("anal", mem, t), t))
        for k in g:
            g[k][m] = h[k]
            a[k][m] = p[f"{k} [m/s]"]
    return ({f"{k} [m/s]": g[k].std(axis=0, ddof=1) for k in g},
            {f"{k} [m/s]": a[k].std(axis=0, ddof=1) for k in a})


def obs_columns():
    """観測のある柱（OBSIN の格子番号 1, 5, …, 117）と、そこから最も遠い柱（2 格子ずつずれた点）の (NY, NX) の bool。"""
    obscol = np.zeros((NY, NX), bool)
    obscol[::OBS_STEP, ::OBS_STEP] = True
    mid = np.zeros((NY, NX), bool)
    mid[2::OBS_STEP, 2::OBS_STEP] = True
    return obscol, mid


def rms(x):
    return np.sqrt(np.mean(x ** 2))


def rmsz(x):
    """層ごとの RMS（NZ,）。"""
    return np.sqrt(np.mean(x ** 2, axis=(1, 2)))


# ---------------------------------------------------------------- 図

C1, C2, C3, GRAY = "#2a78d6", "#eb6834", "#1baf7a", "#8c8b86"


def figdir():
    """図の出力先（環境変数 FIGDIR、必須）。実行ごとに別の場所を指定し、前の結果を上書きしないようにする。"""
    d = os.environ.get("FIGDIR")
    if not d:
        sys.exit("図の出力先を環境変数 FIGDIR で指定してください（例: FIGDIR=../docs/phase7d/run_xxx）。")
    os.makedirs(d, exist_ok=True)
    return d


def use_japanese_font():
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    # ログインノードにはシステムのフォントがあるが、Aquarius の計算ノードにはないので、/work に写したものも探す
    for f in (glob.glob("/usr/share/fonts/vlgothic/VL-PGothic-Regular.ttf") + glob.glob("/work/02/gv42/v42013/fonts/VL-PGothic-Regular.ttf"))[:1]:
        font_manager.fontManager.addfont(f)
        plt.rcParams["font.family"] = "VL PGothic"
    plt.rcParams["axes.unicode_minus"] = False
