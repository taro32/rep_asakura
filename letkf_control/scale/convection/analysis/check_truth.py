#!/usr/bin/env python3
"""7c の ①: 1 cycle の LETKF で、解析が真値（mdet）に近づいたかを全格子点で調べる（Phase 7）。

- 真値: <t+1h>/anal/mdet（mdet の 60 分の予報。LETKF では変わらない。check_letkf.py の 1）。
- 第一推定: <t+1h>/gues/mean（step 7 の 0001–0020 の平均）。解析: <t+1h>/anal/mean。
- 誤差 = 平均 − 真値。全格子点・層ごとの RMSE を、第一推定と解析とで比べる。
  変数は LETKF の状態変数（U, V, W, T, P, QV）と雲・降水の合計。観測しているのは U, V, T だけ。
- ばらつき: T, P, QV, 雲・降水は gues/sprd・anal/sprd（欄の名前と中身が違う。common.physical_sprd の説明）。
  U, V, W は member から直接計算する（common.wind_sprd の説明）。
  ばらつきが誤差と同じくらいなら、アンサンブルは誤差の大きさを正しく見積もっている。
- 誤差の改善の水平分布: 観測のある柱（4 格子おき）とない柱とで、改善の割合を比べる。

出力: 表（標準出力）と FIGDIR/truth_profiles.png・truth_maps.png
使い方: STIME=… OUTDIR=… FIGDIR=… python3 check_truth.py
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import common as cm
from common import NX, NY, physical, physical_sprd, rms, rmsz


def read_restart(mem, kind):
    return cm.read_restart(cm.restart_dir(kind, mem), with_z=True)


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
    wsg, wsa = cm.wind_sprd()
    SG.update(wsg)
    SA.update(wsa)

    # 観測のある柱（OBSIN の格子番号 1, 5, …, 117 = 0 始まりで 0, 4, …, 116）
    obscol, near = cm.obs_columns()                 # near: 観測のある柱から最も遠い柱（4 格子の真ん中 = 2 格子離れた点）

    print("全格子点の RMSE（平均 − 真値）と、ばらつき（RMS）")
    print(f"{'変数':12s} {'RMSE 第一推定':>12s} {'RMSE 解析':>10s} {'解析/第一推定':>12s}"
          f" {'ばらつき 第一推定':>14s} {'ばらつき 解析':>12s}"
          f" {'RMSE/ばらつき':>12s} {'改善 観測の柱':>12s} {'改善 観測の間':>12s} {'改善した層':>10s}")
    for k in T:
        eg, ea = G[k] - T[k], A[k] - T[k]
        rg, ra = rms(eg), rms(ea)
        r_obs = rms(ea[:, obscol]) / rms(eg[:, obscol])
        r_mid = rms(ea[:, near]) / rms(eg[:, near])
        nbetter = int(np.sum(rmsz(ea) < rmsz(eg)))
        print(f"{k:12s} {rg:12.4e} {ra:10.4e} {ra / rg:12.3f} {rms(SG[k]):14.4e} {rms(SA[k]):12.4e}"
              f" {rg / rms(SG[k]):12.2f} {r_obs:12.3f} {r_mid:12.3f} {nbetter:6d}/{len(z)}")
    print("（RMSE/ばらつき = 第一推定の RMSE / 第一推定のばらつき。真値がアンサンブルと同じ分布から来ていれば約 1。改善 = 解析の RMSE / 第一推定の RMSE。観測の柱 = 観測のある 30×30 の柱、観測の間 = そこから 2 格子ずつずれた 30×30 の柱）")

    # 平均の偏り（領域平均の誤差）も見る
    print("\n領域全体の平均の誤差（偏り）: 第一推定 → 解析")
    for k in T:
        print(f"  {k:12s} {np.mean(G[k] - T[k]):+.3e} → {np.mean(A[k] - T[k]):+.3e}")

    # --- 図 1: 層ごとの RMSE とばらつき ---
    out = cm.figdir()
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
    fig.savefig(f"{out}/truth_profiles.png", dpi=110)

    # --- 図 2: U の誤差の水平分布（RMSE が最大の層） ---
    k3 = int(np.argmax(rmsz(G["U [m/s]"] - T["U [m/s]"])))
    eg = (G["U [m/s]"] - T["U [m/s]"])[k3]
    ea = (A["U [m/s]"] - T["U [m/s]"])[k3]
    vmax = np.nanpercentile(np.abs(eg), 99)
    fig, axs = plt.subplots(1, 3, figsize=(15, 4.8))
    for ax, f, ttl in [(axs[0], eg, "first guess − truth"), (axs[1], ea, "analysis − truth"),
                       (axs[2], ea - eg, "increment (analysis − first guess)")]:
        im = ax.pcolormesh(np.arange(NX) * 2, np.arange(NY) * 2, f, cmap="RdBu_r", vmin=-vmax, vmax=vmax)
        ax.set_title(f"U, level {k3 + 1} (z = {z[k3]:.0f} m): {ttl}", fontsize=9)
        ax.set_aspect("equal")
        ax.set_xlabel("x [km]")
        fig.colorbar(im, ax=ax, shrink=0.8, label="m/s")
    jj, ii = np.nonzero(obscol)
    axs[1].plot(ii * 2, jj * 2, "k.", ms=1)
    axs[0].set_ylabel("y [km]")
    fig.tight_layout()
    fig.savefig(f"{out}/truth_maps.png", dpi=110)
    print(f"\n図: {out}/truth_profiles.png, truth_maps.png（U の地図は層 {k3 + 1}）")


if __name__ == "__main__":
    main()
