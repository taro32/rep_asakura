#!/usr/bin/env python3
"""7a の確認: obsmake の観測 obs_20000101010000.dat を、mdet の 60 分の history と照合する（Phase 7）。

- 観測地点（経度・緯度）は OBSIN と同じくモデルの格子点そのものなので、水平方向の内挿はしない。
  経度・緯度がいちばん近い格子点の柱を使う。
- 鉛直方向は、60 分の PRES の log p で線形内挿して観測の気圧での値を出す。
- O − (内挿した値) が、obsmake が足したノイズ（OBSERR = 0.1）程度に収まっていれば合格。
- OBSIN にあって出力にない観測を、「最下層だけ」「柱ごと」「その他」に分け、
  最下層で落ちたものが「60 分の最下層の気圧より地面側」で説明できるかを調べる。

使い方: python3 check_obsmake.py
"""
import glob
import os
import sys
from datetime import datetime, timedelta

import numpy as np
from netCDF4 import Dataset

# 結果の場所。環境変数 OUTDIR で変えられる（退避した結果を読むとき。例: result/bak_soil_1cycle_9829615）
OUTDIR = os.environ.get("OUTDIR", "/work/gv42/v42013/20260923_enkc_convection/result")
# 1 cycle 目の開始時刻。環境変数 STIME で変えられる（Phase 7d の土壌水分摂動の初期値は STIME=20000131000000）
T0 = os.environ.get("STIME", "20000101000000")
T1 = (datetime.strptime(T0, "%Y%m%d%H%M%S") + timedelta(hours=1)).strftime("%Y%m%d%H%M%S")
HIST = f"{OUTDIR}/{T0}/hist/mdet"
OBS = f"{OUTDIR}/obs/obs_{T1}.dat"
OBSIN = "/work/02/gv42/v42013/scale-letkc/letkf_control/scale/convection/make_obsin/obsin/obsin_uvt_intv4"
DX = 2000.0
NX = NY = 120
NZ = 64
T_OBS = 3600.0                                   # 観測の時刻（60 分）
ELMS = {2819: "U", 2820: "V", 3073: "T"}


def read_obs(path):
    raw = np.fromfile(path, dtype="<i4").reshape(-1, 10)
    if not (np.all(raw[:, 0] == 32) and np.all(raw[:, 9] == 32)):
        sys.exit(f"{path}: レコード長が 32 バイトでないレコードがあります。")
    return raw[:, 1:9].copy().view("<f4").astype(np.float64)


def read_global():
    """lon, lat（NY, NX）と、60 分の U, V, T, PRES（NZ, NY, NX）を組み立てる。"""
    lon = np.full((NY, NX), np.nan)
    lat = np.full((NY, NX), np.nan)
    var = {v: np.full((NZ, NY, NX), np.nan) for v in ["U", "V", "T", "PRES"]}
    files = sorted(glob.glob(f"{HIST}/history.pe*.nc"))
    if not files:
        sys.exit(f"history が {HIST} に見つかりません。")
    for f in files:
        with Dataset(f) as d:
            t = np.asarray(d.variables["time"][:])
            it = np.flatnonzero(np.isclose(t, T_OBS))
            if len(it) != 1:
                sys.exit(f"{f}: 時刻 {T_OBS} s がありません（time = {t}）。")
            i = np.rint(d.variables["x"][:] / DX - 0.5).astype(int)
            j = np.rint(d.variables["y"][:] / DX - 0.5).astype(int)
            lon[np.ix_(j, i)] = d.variables["lon"][:]
            lat[np.ix_(j, i)] = d.variables["lat"][:]
            for v in var:
                var[v][:, j[:, None], i[None, :]] = d.variables[v][it[0]]
    if np.isnan(lon).any() or any(np.isnan(a).any() for a in var.values()):
        sys.exit("history から埋まらない格子点があります。")
    return lon, lat, var


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


def main():
    lon, lat, var = read_global()
    obs = read_obs(OBS)
    obsin = read_obs(OBSIN)
    print(f"OBSIN {len(obsin)} 個 → 出力 {len(obs)} 個（落ちたもの {len(obsin) - len(obs)} 個）")

    # --- 1. 出力された観測と history の照合 ---
    jj, ii, dist = nearest_column(lon, lat, obs[:, 1], obs[:, 2])
    print(f"観測地点と格子点のずれ: 最大 {dist.max():.2e} 度")
    print("\n要素  個数     O−H 平均   O−H 標準偏差  |O−H| 最大  誤差   H の範囲")
    for elm, name in ELMS.items():
        sel = np.flatnonzero(obs[:, 0] == elm)
        h = np.array([interp_logp(var[name][:, jj[n], ii[n]], var["PRES"][:, jj[n], ii[n]], obs[n, 3] * 100.0)
                      for n in sel])
        omh = obs[sel, 4] - h
        ok = np.isfinite(omh)
        print(f"{name:4s} {ok.sum():6d}  {omh[ok].mean():+10.4f}  {omh[ok].std():12.4f}  {np.abs(omh[ok]).max():10.4f}"
              f"  {np.unique(obs[sel, 5])}  {h[ok].min():.3f}〜{h[ok].max():.3f}"
              + (f"（内挿できない {(~ok).sum()} 個）" if (~ok).any() else ""))

    # --- 2. 落ちた観測の位置 ---
    # 観測を (要素, 格子点 j, i, 柱の中の気圧の順番) で表し、OBSIN と出力を突き合わせる。
    # 気圧は柱ごとに OBSIN のいちばん近い値に対応させる（浮動小数の丸めで一致しないため）。
    ij_, ii_, _ = nearest_column(lon, lat, obsin[:, 1], obsin[:, 2])
    col_p = {}
    for n in range(len(obsin)):
        col_p.setdefault((ij_[n], ii_[n]), set()).add(obsin[n, 3])
    col_p = {c: np.array(sorted(v, reverse=True)) for c, v in col_p.items()}   # 0 = いちばん下

    def keys(a, jj, ii):
        k = [int(np.argmin(np.abs(col_p[(jj[n], ii[n])] - a[n, 3]))) for n in range(len(a))]
        dp = max(np.min(np.abs(col_p[(jj[n], ii[n])] - a[n, 3])) for n in range(len(a)))
        return [(int(a[n, 0]), jj[n], ii[n], k[n]) for n in range(len(a))], dp

    kin, _ = keys(obsin, ij_, ii_)
    kout, dp = keys(obs, jj, ii)
    print(f"\n出力の気圧と OBSIN の気圧のずれ: 最大 {dp:.2e} hPa")
    miss = sorted(set(kin) - set(kout))
    print(f"落ちた観測 {len(miss)} 個")
    if not miss:
        return
    for elm, name in ELMS.items():
        m = [x for x in miss if x[0] == elm]
        low = [x for x in m if x[3] == 0]
        cols_all = sorted({(x[1], x[2]) for x in m if sum(1 for y in m if y[1:3] == x[1:3]) == len(col_p[x[1:3]])})
        other = [x for x in m if x[3] != 0 and (x[1], x[2]) not in cols_all]
        print(f"  {name}: {len(m)} 個 = 最下層だけ {sum(1 for x in low if (x[1], x[2]) not in cols_all)} 個"
              f" + 柱ごと {len(cols_all)} 本 × {len(col_p[cols_all[0]]) if cols_all else 0} 層"
              f" + その他 {len(other)} 個")
    # 最下層の観測は、気圧が 60 分の最下層の気圧より大きい（地面側）と iqc_out_vlo で落ちる
    # （common/common_obs_scale.f90 の phys2ijk）。この規則だけで説明できるかを、柱ごと落ちた地点を除いて調べる。
    m = [x for x in miss if x[0] == 3073]
    cols_all = sorted({(x[1], x[2]) for x in m if sum(1 for y in m if y[1:3] == x[1:3]) == len(col_p[x[1:3]])})
    lowmiss = {(x[1], x[2]) for x in m if x[3] == 0 and (x[1], x[2]) not in cols_all}
    ncol = ngnd = nmatch = 0
    for (j, i), p in col_p.items():
        if (j, i) in cols_all:
            continue
        ncol += 1
        gnd = p[0] > var["PRES"][0, j, i] * 0.01
        ngnd += gnd
        nmatch += (gnd == ((j, i) in lowmiss))
    print(f"  最下層: 柱ごと落ちた地点を除く {ncol} 地点のうち、観測の気圧が 60 分の最下層の気圧より大きいのは {ngnd} 地点、"
          f"落ちたのは {len(lowmiss)} 地点。両者が一致する地点 {nmatch} / {ncol}")
    print("  柱ごと落ちた地点（格子番号 (j, i)、1 始まり。経度・緯度）:")
    for j, i in cols_all:
        print(f"    ({j + 1}, {i + 1})  {lon[j, i]:.5f}  {lat[j, i]:.5f}")
    print(f"  参考: 南端の行 j = 1 の緯度 {lat[0].min():.5f}〜{lat[0].max():.5f}、"
          f"その 1 つ北 j = 2 の緯度 {lat[1].min():.5f}〜{lat[1].max():.5f}")


if __name__ == "__main__":
    main()
