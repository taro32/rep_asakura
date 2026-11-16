#!/usr/bin/env python3
"""LETKC の制御目標（要素 19001）の試験の検算（2026-11-07。docs/control/20261107_letkc_ctl_plan.md タスク 4）

  1. Y: step 3 の history（<時刻>/hist_gues/<member>/）の PREC（5 分の時間平均）を、目標領域（中心 ±10 km、100 格子）で平均し、
     予報の t + TC ± 15 分（既定 TC = 3600 で time ∈ (2700, 4500]）で積算（× 300 s）。LETKC のログの H(x) と比べる
  2. y* = RATIO × Ȳ、σ_R = FAC × σ_Y（Ȳ・σ_Y は member、分母 N − 1）
  3. ETKF（観測 1 つ・局所化なし・INFL_MUL = 1・RTPP α = 1）で LAND_WATER の第 1・2 層の修正量:
       P̃a = [(N − 1) I + dYᵀ dY / σ_R²]⁻¹
       member: θ_i^a = θ̄ + dX P̃a dYᵀ (y* − Ȳ) / σ_R² + dX_i       （RTPP α = 1 でばらつきは第一推定のまま）
       mdet:   θ_d^a = θ_d + dX P̃a dYᵀ (y* − Y_d) / σ_R²
     そのあと、Δx_mdet < 0 の点は戻す（増やす向きだけ。member = 平均 + 差、mdet = 第一推定）、変わった値を 0〜0.5 に切り詰める
  4. anal − gues と比べる。第 3〜7 層が変わっていないこと
  5. 参考: step 7（予報し直し）の history（hist/）から Y

使い方: python3 check_letkc_ctl_test.py <実験の出力> [--src 初期値の cycle] [--time 20000131120000] [--member 2] [--ratio 0.8] [--fac 1.0] [--tc 3600]
"""
import argparse
import glob
import os

import netCDF4
import numpy as np

XC, YC, HALF = 80.0e3, 120.0e3, 10.0e3
TC, HALF_T = 3600.0, 900.0   # Y の窓 t + TC ± HALF_T（--tc で変える）


def read_global(files, var):
    """pe ごとのファイルを x・y の座標で並べて 1 枚にする"""
    parts = []
    for f in files:
        with netCDF4.Dataset(f) as d:
            parts.append((d["x"][:].data, d["y"][:].data, d[var][:].data))
    xs = np.unique(np.concatenate([p[0] for p in parts]))
    ys = np.unique(np.concatenate([p[1] for p in parts]))
    shp = parts[0][2].shape
    out = None
    for x, y, v in parts:
        ix = np.searchsorted(xs, x)
        iy = np.searchsorted(ys, y)
        if out is None:
            if var == "LAND_WATER":
                out = np.full((len(ys), len(xs), shp[2]), np.nan)
            else:
                out = np.full((shp[0], len(ys), len(xs)), np.nan)
        if var == "LAND_WATER":          # (y, x, lz)
            out[np.ix_(iy, ix)] = v
        else:                            # (time, y, x)
            out[:, iy[:, None], ix[None, :]] = v
    return xs, ys, out


def calc_y(histdir):
    files = sorted(glob.glob(f"{histdir}/history.pe*.nc"))
    with netCDF4.Dataset(files[0]) as d:
        t = d["time"][:].data
    t = t - t[0]
    xs, ys, prec = read_global(files, "PREC")
    kt = (t > TC - HALF_T + 1e-3) & (t <= TC + HALF_T + 1e-3)
    mx = np.abs(xs - XC) <= HALF + 1e-3
    my = np.abs(ys - YC) <= HALF + 1e-3
    sub = prec[kt][:, my][:, :, mx]
    return sub.sum(axis=0).mean() * 300.0, int(kt.sum()), int(mx.sum() * my.sum()), t[kt]


def read_lw(d):
    files = sorted(glob.glob(f"{d}/init_*.pe*.nc"))
    _, _, lw = read_global(files, "LAND_WATER")
    return lw   # (y, x, lz)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("out")
    p.add_argument("--src", default="/work/gv42/v42013/20260923_enkc_convection/result_m80")
    p.add_argument("--time", default="20000131120000")
    p.add_argument("--member", type=int, default=2)
    p.add_argument("--ratio", type=float, default=0.8)
    p.add_argument("--fac", type=float, default=1.0)
    p.add_argument("--tc", type=float, default=3600.0)
    a = p.parse_args()
    global TC
    TC = a.tc
    T = a.time
    mems = [f"{m:04d}" for m in range(1, a.member + 1)]

    print("== 1. Y（step 3 の history、hist_gues）")
    Y = {}
    for m in mems + ["mdet"]:
        Y[m], nk, nc, tk = calc_y(f"{a.out}/{T}/hist_gues/{m}")
        print(f"  {m}: Y = {Y[m]:.6e} mm（スロット {nk} 個 t = {tk.astype(int).tolist()}、格子 {nc}）")
    Ym = np.array([Y[m] for m in mems])
    N = len(mems)
    ybar, sy = Ym.mean(), Ym.std(ddof=1)
    ystar, sr = a.ratio * ybar, a.fac * sy
    print(f"== 2. Ybar = {ybar:.6e}, sigma_Y = {sy:.6e}, y* = {ystar:.6e}, sigma_R = {sr:.6e}")
    print(f"  departure: member 平均 y* − Ybar = {ystar - ybar:.6e}, mdet y* − Y_mdet = {ystar - Y['mdet']:.6e}")

    print("== 3. ETKF の修正量（LAND_WATER の第 1・2 層）")
    dY = (Ym - ybar)[None, :]                       # (1, N)
    Pa = np.linalg.inv((N - 1) * np.eye(N) + dY.T @ dY / sr**2)
    wm = Pa @ dY.T[:, 0] * (ystar - ybar) / sr**2   # (N,)
    wd = Pa @ dY.T[:, 0] * (ystar - Y["mdet"]) / sr**2
    print(f"  transm = {wm}, transmd = {wd}")

    gm = {m: read_lw(f"{a.src}/{T}/anal/{m}") for m in mems}   # member の第一推定 = 初期値（コピー元）
    am = {m: read_lw(f"{a.out}/{T}/anal/{m}") for m in mems}
    gd = read_lw(f"{a.out}/{T}/gues/mdet")
    ad = read_lw(f"{a.out}/{T}/anal/mdet")
    X = np.stack([gm[m] for m in mems])            # (N, y, x, lz)
    xbar = X.mean(axis=0)
    dX = X - xbar
    dmean = np.tensordot(wm, dX, axes=(0, 0))
    dmdet = np.tensordot(wd, dX, axes=(0, 0))
    for lz in range(7):
        same_d = np.array_equal(ad[..., lz], gd[..., lz])
        same_m = all(np.array_equal(am[m][..., lz], gm[m][..., lz]) for m in mems)
        print(f"  層 {lz + 1}: mdet 変化なし = {same_d}, member 変化なし = {same_m}")
    for lz in (0, 1):
        # 予測（制約の前）
        pd = gd[..., lz] + dmdet[..., lz]
        keep = (pd - gd[..., lz]) > 0          # 増やす向きだけ（Δx_mdet で判定）
        pd = np.where(keep, np.clip(pd, 0.0, 0.5), gd[..., lz])
        real = ad[..., lz] - gd[..., lz]
        pred = pd - gd[..., lz]
        print(f"  層 {lz + 1} mdet: 修正した格子 実際 {int((real != 0).sum())} / 予測 {int(keep.sum())}、"
              f"max Δ 実際 {real.max():.4e} / 予測 {pred.max():.4e}、max |実際 − 予測| = {np.abs(real - pred).max():.3e}、"
              f"Σ Δ 実際 {real.sum():.4e} / 予測 {pred.sum():.4e}")
        for i, m in enumerate(mems):
            pm = xbar[..., lz] + dmean[..., lz] + dX[i][..., lz]
            pm = np.where(keep, np.clip(pm, 0.0, 0.5), gm[m][..., lz])
            real = am[m][..., lz] - gm[m][..., lz]
            pred = pm - gm[m][..., lz]
            print(f"  層 {lz + 1} member {m}: 修正した格子 実際 {int((real != 0).sum())}、max Δ 実際 {real.max():.4e} / 予測 {pred.max():.4e}、"
                  f"max |実際 − 予測| = {np.abs(real - pred).max():.3e}")
        print(f"  層 {lz + 1}: member の第一推定のばらつき max = {dX[..., lz].std(axis=0, ddof=1).max():.4e}")

    print("== 5. 参考: step 7（予報し直し）の history の Y")
    for m in mems + ["mdet"]:
        d = f"{a.out}/{T}/hist/{m}"
        if os.path.isdir(d):
            y7, _, _, _ = calc_y(d)
            print(f"  {m}: Y = {y7:.6e} mm（修正前 {Y[m]:.6e}）")


if __name__ == "__main__":
    main()
