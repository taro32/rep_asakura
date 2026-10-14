#!/usr/bin/env python3
"""7b の確認: LETKF（step 10）の結果を見る（Phase 7）。

1. mdet は LETKF で変わっていないか（DET_RUN_UPDATE = 2）:
   <t+1h>/anal/mdet の restart と、step 7 の mdet の 60 分の history（DENS, RHOT, QV）を比べる。
2. 増分 anal/mean − gues/mean の大きさと水平分布（U, V は MOMX, MOMY を格子の中心へ平均して DENS で割る。PT = RHOT/DENS）。
   二重周期の境界の近く（端から 8 格子以内）と内側とで、増分の大きさを比べる。
3. ばらつき gues/sprd と anal/sprd（U は sprd の MOMX を mean の DENS で割った近似、QV はそのまま）。
4. 観測地点での O−B・O−A を restart から自分で計算し、LETKF のログの統計と比べる（U, V）。
   鉛直の内挿には mdet の 60 分の PRES を使う（check_obsmake.py と同じ）。

使い方: python3 check_letkf.py
"""
import glob
import sys

import numpy as np
from netCDF4 import Dataset

import check_obsmake as co

OUTDIR = co.OUTDIR
T0, T1 = co.T0, co.T1                              # 環境変数 STIME で変えられる（check_obsmake.py）
LABEL = f"init_{T1[0:8]}-{T1[8:14]}.000"
DX = co.DX
NX, NY, NZ = co.NX, co.NY, co.NZ
EDGE = 8                                           # 境界の近くとみなす格子数
GROSS = 5.0 * 0.1                                  # LETKF の QC（GROSS_ERROR × 観測誤差）


def read_restart(mem, kind="anal"):
    """<t+1h>/<kind>/<mem> の restart から DENS, MOMX, MOMY, RHOT, QV を (NZ, NY, NX) で組み立てる。"""
    files = sorted(glob.glob(f"{OUTDIR}/{T1}/{kind}/{mem}/{LABEL}.pe*.nc"))
    if len(files) != 144:
        sys.exit(f"{kind}/{mem}: ファイルが {len(files)} 個です。")
    out = {v: np.full((NZ, NY, NX), np.nan) for v in ["DENS", "MOMX", "MOMY", "RHOT", "QV"]}
    for f in files:
        with Dataset(f) as d:
            i = np.rint(d.variables["x"][:] / DX - 0.5).astype(int)
            j = np.rint(d.variables["y"][:] / DX - 0.5).astype(int)
            for v in out:
                out[v][:, j[:, None], i[None, :]] = d.variables[v][:].transpose(2, 0, 1)
    return out


def center(r, dens):
    """MOMX（x の面）・MOMY（y の面）を格子の中心へ平均し（二重周期）、dens で割って U, V にする。"""
    u = 0.5 * (r["MOMX"] + np.roll(r["MOMX"], 1, axis=2)) / dens
    v = 0.5 * (r["MOMY"] + np.roll(r["MOMY"], 1, axis=1)) / dens
    return u, v


def read_hist(mem, t):
    files = sorted(glob.glob(f"{OUTDIR}/{T0}/hist/{mem}/history.pe*.nc"))
    out = {v: np.full((NZ, NY, NX), np.nan) for v in ["DENS", "RHOT", "QV"]}
    for f in files:
        with Dataset(f) as d:
            it = int(np.flatnonzero(np.isclose(d.variables["time"][:], t))[0])
            i = np.rint(d.variables["x"][:] / DX - 0.5).astype(int)
            j = np.rint(d.variables["y"][:] / DX - 0.5).astype(int)
            for v in out:
                out[v][:, j[:, None], i[None, :]] = d.variables[v][it]
    return out


def rms(x):
    return np.sqrt(np.mean(x ** 2))


def main():
    # --- 1. mdet ---
    am = read_restart("mdet")
    hm = read_hist("mdet", 3600.0)
    print("1. anal/mdet（t+1h）と step 7 の mdet の 60 分の history の相対差（history は real(4)）")
    for v in ["DENS", "RHOT", "QV"]:
        r = np.abs(am[v] - hm[v]) / np.maximum(np.abs(hm[v]), 1e-30)
        print(f"   {v:4s}: 相対差 最大 {np.nanmax(r):.2e}")

    # --- 2. 増分 ---
    a = read_restart("mean", "anal")
    g = read_restart("mean", "gues")
    aU, aV = center(a, a["DENS"])
    gU, gV = center(g, g["DENS"])
    fields = {"U": (aU - gU, "m/s"), "V": (aV - gV, "m/s"),
              "PT": (a["RHOT"] / a["DENS"] - g["RHOT"] / g["DENS"], "K"), "QV": (a["QV"] - g["QV"], "kg/kg")}
    edge = np.zeros((NY, NX), bool)
    edge[:EDGE, :] = edge[-EDGE:, :] = True
    edge[:, :EDGE] = edge[:, -EDGE:] = True
    print("\n2. 増分 anal/mean − gues/mean")
    print("   変数  RMS         最大 |.|     増分が 0 の柱の割合  境界付近の RMS  内側の RMS   RMS 最大の層（1 始まり）")
    for v, (inc, unit) in fields.items():
        col = np.sqrt(np.mean(inc ** 2, axis=0))
        lev = np.sqrt(np.mean(inc ** 2, axis=(1, 2)))
        print(f"   {v:4s}  {rms(inc):.3e}   {np.abs(inc).max():.3e}   {np.mean(col == 0):.3f}               "
              f"{rms(col[edge]):.3e}      {rms(col[~edge]):.3e}    {int(np.argmax(lev)) + 1}  [{unit}]")

    # --- 3. ばらつき ---
    sa = read_restart("sprd", "anal")
    sg = read_restart("sprd", "gues")
    sgU, _ = center(sg, g["DENS"])
    saU, _ = center(sa, a["DENS"])
    print("\n3. ばらつき（全格子点での RMS）")
    print("   変数  gues          anal          anal / gues")
    for v, fg, fa in [("U", sgU, saU), ("QV", sg["QV"], sa["QV"])]:
        print(f"   {v:4s}  {rms(fg):.3e}     {rms(fa):.3e}     {rms(fa) / rms(fg):.3f}")
    print("   層ごとの U（gues → anal）:")
    for k in [0, 7, 15, 31, 47, 63]:
        print(f"     層 {k + 1:2d}: {rms(sgU[k]):.3e} → {rms(saU[k]):.3e}")

    # --- 4. 観測空間 ---
    lon, lat, var = co.read_global()               # mdet の 60 分（PRES を鉛直の内挿に使う）
    obs = co.read_obs(co.OBS)
    jj, ii, _ = co.nearest_column(lon, lat, obs[:, 1], obs[:, 2])
    mU, mV = center(am, am["DENS"])
    print(f"\n4. 観測地点での比較（QC は |O−B| < {GROSS}。LETKF のログの統計と比べる）")
    print("   要素  QC 後の個数  O−B     O−A     |A−B|   O−mdet  | QC 前: O−B    B−mdet  gues のばらつき")
    for elm, name, G, A, M, S in [(2819, "U", gU, aU, mU, sgU), (2820, "V", gV, aV, mV, None)]:
        sel = np.flatnonzero(obs[:, 0] == elm)

        def h(f):
            return np.array([co.interp_logp(f[:, jj[n], ii[n]], var["PRES"][:, jj[n], ii[n]], obs[n, 3] * 100.0)
                             for n in sel])
        o = obs[sel, 4]
        hb, ha, hmd = h(G), h(A), h(M)
        ok = np.isfinite(hb) & np.isfinite(ha)
        qc = ok & (np.abs(o - hb) < GROSS)
        sp = f"{rms(h(S)[ok]):.4f}" if S is not None else "—"
        print(f"   {name:4s}  {qc.sum():11d}  {rms((o - hb)[qc]):.4f}  {rms((o - ha)[qc]):.4f}  {rms((ha - hb)[qc]):.4f}  "
              f"{rms((o - hmd)[qc]):.4f}  |        {rms((o - hb)[ok]):.4f}  {rms((hb - hmd)[ok]):.4f}  {sp}")


if __name__ == "__main__":
    main()
