#!/usr/bin/env python3
"""7c の ①: 1 cycle の LETKF で、解析が真値（mdet）に近づいたかを全格子点で調べる（Phase 7）。

- 真値: <t+1h>/anal/mdet（mdet の 60 分の予報。LETKF では変わらない。check_letkf.py の 1）。
- 第一推定: <t+1h>/gues/mean（step 7 の 0001–0020 の平均）。解析: <t+1h>/anal/mean。
- 誤差 = 平均 − 真値。全格子点・層ごとの RMSE を、第一推定と解析とで比べる。
  変数は LETKF の状態変数（U, V, W, T, P, QV）と雲・降水の合計。観測しているのは U, V, T だけ。
- ばらつき: T, P, QV, 雲・降水は gues/sprd・anal/sprd（欄の名前と中身が違う。physical_sprd の説明）。
  U, V, W は member から直接計算する（wind_sprd_members の説明）。
  ばらつきが誤差と同じくらいなら、アンサンブルは誤差の大きさを正しく見積もっている。
- 誤差の改善の水平分布: 観測のある柱（4 格子おき）とない柱とで、改善の割合を比べる。

出力: 表（標準出力）と figs/truth_profiles.png・figs/truth_maps.png
使い方: python3 check_truth.py
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from netCDF4 import Dataset

import check_letkf as cl

VARS3 = ["DENS", "MOMX", "MOMY", "MOMZ", "RHOT", "QV", "QC", "QR", "QI", "QS", "QG"]
HERE = os.path.dirname(os.path.abspath(__file__))
OBS_STEP = 4                                       # OBSIN の水平の間隔（格子番号 1, 5, …, 117）


def read_restart(mem, kind):
    """cl.read_restart と同じだが、MOMZ と雲・降水も読む。MOMZ は zh の 65 層のまま。"""
    import glob
    files = sorted(glob.glob(f"{cl.OUTDIR}/{cl.T1}/{kind}/{mem}/{cl.LABEL}.pe*.nc"))
    assert len(files) == 144, f"{kind}/{mem}: {len(files)} files"
    out = {}
    for f in files:
        with Dataset(f) as d:
            i = np.rint(d.variables["x"][:] / cl.DX - 0.5).astype(int)
            j = np.rint(d.variables["y"][:] / cl.DX - 0.5).astype(int)
            for v in VARS3:
                a = d.variables[v][:].transpose(2, 0, 1)
                if v not in out:
                    out[v] = np.full((a.shape[0], cl.NY, cl.NX), np.nan)
                out[v][:, j[:, None], i[None, :]] = a
            z = np.asarray(d.variables["z"][:])
    return out, z


# SCALE の定数（scale_const）
RDRY, RVAP, CVDRY, CVVAP, CL, CI, P00 = 287.04, 461.46, 717.60, 1384.14, 4218.0, 2106.0, 1.0e5


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
    """restart（mean・mdet）の予報変数を、LETKF の状態変数（U, V, W, T, P, QV）と雲・降水の合計に直す。"""
    u, v = cl.center(r, r["DENS"])
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


def wind_sprd_members():
    """U, V, W のばらつきを member から直接計算する（格子の中心の値。誤差と同じ定義にそろえる）。
    LETKF の sprd の U, V, W は格子の面などの値で、中心へ平均した値より 1.5 倍ほど大きく出るので使わない。
    第一推定: step 7 の各 member の 60 分の history（U, V, W は格子の中心の値）。
    解析: anal/0001–0020 の restart を physical と同じ式で中心へ直す。"""
    import glob
    hist = {k: np.empty((20, cl.NZ, cl.NY, cl.NX)) for k in ["U", "V", "W"]}
    for m in range(20):
        for f in sorted(glob.glob(f"{cl.OUTDIR}/{cl.T0}/hist/{m + 1:04d}/history.pe*.nc")):
            with Dataset(f) as d:
                it = int(np.flatnonzero(np.isclose(d.variables["time"][:], 3600.0))[0])
                i = np.rint(d.variables["x"][:] / cl.DX - 0.5).astype(int)
                j = np.rint(d.variables["y"][:] / cl.DX - 0.5).astype(int)
                for k in hist:
                    hist[k][m][:, j[:, None], i[None, :]] = d.variables[k][it]
    anal = {k: np.empty((20, cl.NZ, cl.NY, cl.NX)) for k in ["U", "V", "W"]}
    for m in range(20):
        r, _ = read_restart(f"{m + 1:04d}", "anal")
        p = physical(r)
        for k in anal:
            anal[k][m] = p[f"{k} [m/s]"]
    sg = {f"{k} [m/s]": hist[k].std(axis=0, ddof=1) for k in hist}
    sa = {f"{k} [m/s]": anal[k].std(axis=0, ddof=1) for k in anal}
    return sg, sa


def rmsz(x):
    """層ごとの RMS（NZ,）。"""
    return np.sqrt(np.mean(x ** 2, axis=(1, 2)))


def main():
    t, z = read_restart("mdet", "anal")
    g, _ = read_restart("mean", "gues")
    a, _ = read_restart("mean", "anal")
    sg, _ = read_restart("sprd", "gues")
    sa, _ = read_restart("sprd", "anal")

    T = physical(t)
    G = physical(g)
    A = physical(a)
    SG = physical_sprd(sg)
    SA = physical_sprd(sa)
    wsg, wsa = wind_sprd_members()
    SG.update(wsg)
    SA.update(wsa)

    # 観測のある柱（OBSIN の格子番号 1, 5, …, 117 = 0 始まりで 0, 4, …, 116）
    obscol = np.zeros((cl.NY, cl.NX), bool)
    obscol[::OBS_STEP, ::OBS_STEP] = True
    near = np.zeros((cl.NY, cl.NX), bool)          # 観測のある柱から最も遠い柱（4 格子の真ん中 = 2 格子離れた点）
    near[2::OBS_STEP, 2::OBS_STEP] = True

    print("全格子点の RMSE（平均 − 真値）と、ばらつき（RMS）")
    print(f"{'変数':12s} {'RMSE 第一推定':>12s} {'RMSE 解析':>10s} {'解析/第一推定':>12s}"
          f" {'ばらつき 第一推定':>14s} {'ばらつき 解析':>12s}"
          f" {'RMSE/ばらつき':>12s} {'改善 観測の柱':>12s} {'改善 観測の間':>12s} {'改善した層':>10s}")
    for k in T:
        eg, ea = G[k] - T[k], A[k] - T[k]
        rg, ra = cl.rms(eg), cl.rms(ea)
        r_obs = cl.rms(ea[:, obscol]) / cl.rms(eg[:, obscol])
        r_mid = cl.rms(ea[:, near]) / cl.rms(eg[:, near])
        nbetter = int(np.sum(rmsz(ea) < rmsz(eg)))
        print(f"{k:12s} {rg:12.4e} {ra:10.4e} {ra / rg:12.3f} {cl.rms(SG[k]):14.4e} {cl.rms(SA[k]):12.4e}"
              f" {rg / cl.rms(SG[k]):12.2f} {r_obs:12.3f} {r_mid:12.3f} {nbetter:6d}/{len(z)}")
    print("（RMSE/ばらつき = 第一推定の RMSE / 第一推定のばらつき。真値がアンサンブルと同じ分布から来ていれば約 1。改善 = 解析の RMSE / 第一推定の RMSE。観測の柱 = 観測のある 30×30 の柱、観測の間 = そこから 2 格子ずつずれた 30×30 の柱）")

    # 平均の偏り（領域平均の誤差）も見る
    print("\n領域全体の平均の誤差（偏り）: 第一推定 → 解析")
    for k in T:
        print(f"  {k:12s} {np.mean(G[k] - T[k]):+.3e} → {np.mean(A[k] - T[k]):+.3e}")

    # --- 図 1: 層ごとの RMSE とばらつき ---
    os.makedirs(f"{HERE}/figs", exist_ok=True)
    keys = list(T)
    fig, axs = plt.subplots(1, len(keys), figsize=(3.0 * len(keys), 5.5), sharey=True)
    zk = z / 1e3
    for ax, k in zip(axs, keys):
        ax.plot(rmsz(G[k] - T[k]), zk, color="#1f77b4", label="RMSE first guess")
        ax.plot(rmsz(A[k] - T[k]), zk, color="#d62728", label="RMSE analysis")
        ax.plot(rmsz(SG[k]), zk, color="#1f77b4", ls="--", label="spread first guess")
        ax.plot(rmsz(SA[k]), zk, color="#d62728", ls="--", label="spread analysis")
        ax.set_title(k, fontsize=10)
        ax.grid(alpha=0.3)
        ax.set_xlim(left=0)
    axs[0].set_ylabel("height [km]")
    axs[0].legend(fontsize=7, loc="upper right")
    fig.suptitle("1 cycle (t = 60 min): error vs truth (mdet) over all grid points, by level", fontsize=11)
    fig.tight_layout()
    fig.savefig(f"{HERE}/figs/truth_profiles.png", dpi=110)

    # --- 図 2: U の誤差の水平分布（RMSE が最大の層） ---
    k3 = int(np.argmax(rmsz(G["U [m/s]"] - T["U [m/s]"])))
    eg = (G["U [m/s]"] - T["U [m/s]"])[k3]
    ea = (A["U [m/s]"] - T["U [m/s]"])[k3]
    vmax = np.nanpercentile(np.abs(eg), 99)
    fig, axs = plt.subplots(1, 3, figsize=(15, 4.8))
    for ax, f, ttl in [(axs[0], eg, "first guess − truth"), (axs[1], ea, "analysis − truth"),
                       (axs[2], ea - eg, "increment (analysis − first guess)")]:
        im = ax.pcolormesh(np.arange(cl.NX) * 2, np.arange(cl.NY) * 2, f, cmap="RdBu_r", vmin=-vmax, vmax=vmax)
        ax.set_title(f"U, level {k3 + 1} (z = {z[k3]:.0f} m): {ttl}", fontsize=9)
        ax.set_aspect("equal")
        ax.set_xlabel("x [km]")
        fig.colorbar(im, ax=ax, shrink=0.8, label="m/s")
    jj, ii = np.nonzero(obscol)
    axs[1].plot(ii * 2, jj * 2, "k.", ms=1)
    axs[0].set_ylabel("y [km]")
    fig.tight_layout()
    fig.savefig(f"{HERE}/figs/truth_maps.png", dpi=110)
    print(f"\n図: {HERE}/figs/truth_profiles.png, truth_maps.png（U の地図は層 {k3 + 1}）")


if __name__ == "__main__":
    main()
