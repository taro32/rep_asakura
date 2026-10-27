#!/usr/bin/env python3
"""7b の確認: LETKF（step 10）の結果を見る（Phase 7）。

1. mdet は LETKF で変わっていないか（DET_RUN_UPDATE = 2）:
   <t+1h>/anal/mdet の restart と、step 7 の mdet の 60 分の history（DENS, RHOT, QV）を比べる。
2. 増分 anal/mean − gues/mean の大きさと水平分布（U, V は MOMX, MOMY を格子の中心へ平均して DENS で割る。PT = RHOT/DENS）。
   二重周期の境界の近く（端から 8 格子以内）と内側とで、増分の大きさを比べる。
3. ばらつき gues/sprd と anal/sprd（U は sprd の MOMX を mean の DENS で割った近似、QV はそのまま）。
4. 観測地点での O−B・O−A を restart から自分で計算し、LETKF のログの統計と比べる（U, V）。
   鉛直の内挿には mdet の 60 分の PRES を使う（check_obsmake.py と同じ）。

使い方: STIME=… OUTDIR=… python3 check_letkf.py
"""
import numpy as np

import common as cm
from common import GROSS, NX, NY, center, rms

EDGE = 8                                           # 境界の近くとみなす格子数
VARS = ["DENS", "MOMX", "MOMY", "RHOT", "QV"]


def read_restart(mem, kind="anal"):
    """<t+1h>/<kind>/<mem> の restart から DENS, MOMX, MOMY, RHOT, QV を (NZ, NY, NX) で組み立てる。"""
    return cm.read_restart(cm.restart_dir(kind, mem), names=VARS)


def main():
    # --- 1. mdet ---
    am = read_restart("mdet")
    hm = cm.read_hist(cm.hist_dir("mdet"), ["DENS", "RHOT", "QV"])
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
    lon, lat, var = cm.read_global(cm.hist_dir("mdet"))   # mdet の 60 分（PRES を鉛直の内挿に使う）
    obs = cm.read_obs(cm.OBS)
    jj, ii, _ = cm.nearest_column(lon, lat, obs[:, 1], obs[:, 2])
    mU, mV = center(am, am["DENS"])
    print(f"\n4. 観測地点での比較（QC は |O−B| < {GROSS}。LETKF のログの統計と比べる）")
    print("   要素  QC 後の個数  O−B     O−A     |A−B|   O−mdet  | QC 前: O−B    B−mdet  gues のばらつき")
    for elm, name, G, A, M, S in [(2819, "U", gU, aU, mU, sgU), (2820, "V", gV, aV, mV, None)]:
        sel = np.flatnonzero(obs[:, 0] == elm)

        def h(f):
            return cm.obs_operator(f, var["PRES"], obs, jj, ii, sel)
        o = obs[sel, 4]
        hb, ha, hmd = h(G), h(A), h(M)
        ok = np.isfinite(hb) & np.isfinite(ha)
        qc = ok & (np.abs(o - hb) < GROSS)
        sp = f"{rms(h(S)[ok]):.4f}" if S is not None else "—"
        print(f"   {name:4s}  {qc.sum():11d}  {rms((o - hb)[qc]):.4f}  {rms((o - ha)[qc]):.4f}  {rms((ha - hb)[qc]):.4f}  "
              f"{rms((o - hmd)[qc]):.4f}  |        {rms((o - hb)[ok]):.4f}  {rms((hb - hmd)[ok]):.4f}  {sp}")


if __name__ == "__main__":
    main()
