#!/usr/bin/env python3
"""7b の原因調べ: LETKF の平均の更新を Python で再現し、設定を変えたときに解析がどう変わるかを見る（Phase 7）。

- 第一推定: step 7 の各 member（0001–0020）の 60 分の history（U, V, T, PRES）。観測地点で log p について線形内挿する。
- 観測: obs_20000101010000.dat（obsmake の出力）。観測誤差 0.1。
- 式（SCALE-LETKF と同じ。平均の更新だけ）:
    重み   w = exp(-0.5 (dh²/L² + dv²/Lv²))、dh・dv/Lv が 3.65 L を超える観測は使わない
           （dh は格子番号の差 × 2 km。二重周期の境界はまたがない。dv = |ln p − ln p_o|）
    Pa~  = [(K−1)/INFL_MUL I + Yb^T R_loc^-1 Yb]^-1、R_loc = err² / w
    増分  = Yb_e · Pa~ Yb^T R_loc^-1 d（評価する観測の位置での、観測空間の増分）
- 評価: QC を通った U の観測から無作為に選んだ点で、O−B・O−A と、実際の LETKF の A−B（restart から）を比べる。
  まず既定の設定で実際の LETKF と合うことを確かめ、そのあと設定を 1 つずつ変える。

使い方: python3 offline_letkf.py
"""
import glob

import numpy as np
from netCDF4 import Dataset

import check_obsmake as co
import check_letkf as cl

NMEM = 20
ERR = 0.1
INFL = 1.45
FAC = 2.0 * np.sqrt(10.0 / 3.0)                  # 打ち切り（L の 3.65 倍）
NEVAL = 400
rng = np.random.default_rng(0)


def read_members():
    """各 member の 60 分の U, V, T, PRES を (NMEM, NZ, NY, NX) で返す。"""
    out = {v: np.empty((NMEM, co.NZ, co.NY, co.NX), np.float32) for v in ["U", "V", "T", "PRES"]}
    for m in range(NMEM):
        for f in sorted(glob.glob(f"{co.OUTDIR}/{cl.T0}/hist/{m + 1:04d}/history.pe*.nc")):
            with Dataset(f) as d:
                it = int(np.flatnonzero(np.isclose(d.variables["time"][:], 3600.0))[0])
                i = np.rint(d.variables["x"][:] / co.DX - 0.5).astype(int)
                j = np.rint(d.variables["y"][:] / co.DX - 0.5).astype(int)
                for v in out:
                    out[v][m][:, j[:, None], i[None, :]] = d.variables[v][it]
    return out


def interp_cols(f, lp, jj, ii, lpo):
    """f, lp: (NZ, NY, NX)。柱 (jj, ii) で ln p について線形内挿し、lpo での値を返す（範囲外は nan）。"""
    fc = f[:, jj, ii]
    lc = lp[:, jj, ii]                             # 下（大きい）→ 上（小さい）
    k = np.sum(lc >= lpo[None, :], axis=0) - 1     # lc[k] >= lpo > lc[k+1]
    ok = (k >= 0) & (k < co.NZ - 1)
    k = np.clip(k, 0, co.NZ - 2)
    n = np.arange(len(lpo))
    w = (lpo - lc[k + 1, n]) / (lc[k, n] - lc[k + 1, n])
    val = w * fc[k, n] + (1 - w) * fc[k + 1, n]
    return np.where(ok, val, np.nan)


def main():
    lon, lat, _ = co.read_global()
    obs = co.read_obs(co.OBS)
    jj, ii, _ = co.nearest_column(lon, lat, obs[:, 1], obs[:, 2])
    lpo = np.log(obs[:, 3] * 100.0)
    mem = read_members()

    # 第一推定の観測空間 H(x_m)
    name = {2819: "U", 2820: "V", 3073: "T"}
    hx = np.full((NMEM, len(obs)), np.nan)
    for m in range(NMEM):
        lp = np.log(mem["PRES"][m].astype(np.float64))
        for elm, v in name.items():
            s = obs[:, 0] == elm
            hx[m, s] = interp_cols(mem[v][m], lp, jj[s], ii[s], lpo[s])
    ok = np.all(np.isfinite(hx), axis=0)
    hb = hx.mean(axis=0)
    Yb = hx - hb                                   # (NMEM, nobs)
    d = obs[:, 4] - hb
    qc = ok & (np.abs(d) < 5.0 * ERR)
    print(f"観測 {len(obs)} 個、内挿できたもの {ok.sum()}、QC 後 {qc.sum()}")

    # 実際の LETKF の A−B（restart の mean から。check_letkf.py と同じ）
    a = cl.read_restart("mean", "anal")
    g = cl.read_restart("mean", "gues")
    aU, _ = cl.center(a, a["DENS"])
    gU, _ = cl.center(g, g["DENS"])
    _, _, var = co.read_global()
    evals = rng.choice(np.flatnonzero(qc & (obs[:, 0] == 2819)), NEVAL, replace=False)
    lp_m = np.log(var["PRES"])
    real_inc = (interp_cols(aU, lp_m, jj[evals], ii[evals], lpo[evals])
                - interp_cols(gU, lp_m, jj[evals], ii[evals], lpo[evals]))

    def run(label, L=20e3, Lv=0.3, use=None, infl=INFL, single=False):
        """use: 使う観測（既定は QC 後の全部）。評価点の観測そのものは必ず使う。single: 評価点の観測 1 個だけを使う。"""
        use = qc if use is None else use
        inc = np.empty(NEVAL)
        nloc = np.empty(NEVAL)
        neff = np.empty(NEVAL)
        for e, n in enumerate(evals):
            idx = np.array([n]) if single else np.union1d(np.flatnonzero(use), [n])
            dh = np.hypot((jj[idx] - jj[n]) * co.DX, (ii[idx] - ii[n]) * co.DX) / L
            dv = np.abs(lpo[idx] - lpo[n]) / Lv
            nd2 = dh ** 2 + dv ** 2
            sel = (dh <= FAC) & (dv <= FAC) & (nd2 <= FAC ** 2)
            o = idx[sel]
            w = np.exp(-0.5 * nd2[sel])
            rinv = w / ERR ** 2
            Y = Yb[:, o]                           # (NMEM, nl)
            A = (NMEM - 1) / infl * np.eye(NMEM) + (Y * rinv) @ Y.T
            wbar = np.linalg.solve(A, (Y * rinv) @ d[o])
            inc[e] = Yb[:, n] @ wbar
            nloc[e] = len(o)
            neff[e] = w.sum()
        omb = d[evals]
        oma = omb - inc
        r = lambda x: np.sqrt(np.mean(x ** 2))
        print(f"  {label:34s} O−B {r(omb):.4f}  O−A {r(oma):.4f}  |A−B| {r(inc):.4f}  "
              f"局所の観測数 {np.median(nloc):7.0f}（重みの和 {np.median(neff):6.0f}）")
        return inc

    print(f"\n評価点: QC を通った U の観測から {NEVAL} 点。実際の LETKF の |A−B| = {np.sqrt(np.nanmean(real_inc ** 2)):.4f}")
    base = run("既定（L=20km, Lv=0.3, QC あり）")
    m = np.isfinite(real_inc)
    print(f"    ↑ 実際の LETKF の増分との相関 {np.corrcoef(base[m], real_inc[m])[0, 1]:.3f}、"
          f"回帰係数 {np.polyfit(real_inc[m], base[m], 1)[0]:.3f}")
    run("QC なし", use=ok)
    run("L = 8 km", L=8e3)
    run("L = 4 km", L=4e3)
    run("L = 2 km", L=2e3)
    thin = qc & (jj % 8 == 0) & (ii % 8 == 0)      # 16 km おき
    run("観測を 16 km おきに間引く", use=thin)
    run("評価点の観測 1 個だけ", single=True)


if __name__ == "__main__":
    main()
