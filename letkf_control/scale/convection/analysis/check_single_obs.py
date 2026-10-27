#!/usr/bin/env python3
"""1 点観測試験（Phase 7d「感度実験 3 回目」、7c の ②）の確認。

S1U・S1T は、C' の 5 時の解析から 1 時間予報し、6 時の LETKF を 4 つの孤立した観測（互いに 120 km、局所化の打ち切り約 73 km より遠い）
だけで行った。それぞれの点の局所解析には、その観測 1 つだけが効く。

1. 観測の点: LETKF の O−A / O−B（obsdep）を、観測 1 個のときの理論値と比べる。
   理論値 = σ_o² / (INFL_MUL σ_b² + σ_o²)（σ_b は obsdep の第一推定のばらつき = inflation の前、σ_o = 0.1。RTPP は平均を変えない）。
   あわせて、真値とのずれ d_b = H(第一推定の平均) − H(真値)、d_a = H(解析の平均) − H(真値)（真値は基準の mdet）。
2. まわり: 観測に近い層で、LETKF の修正（解析 − 第一推定）と必要な修正（真値 − 第一推定）の水平分布を並べる（観測のまわり ±60 km）。

出力: 表（標準出力）と docs/phase7d/sens/single_obs_<実験名>.png
使い方: cd analysis && python3 check_single_obs.py S1U [S1T …]
"""
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import common as cm
from common import NX, NY, OBSERR, physical

T = "20000131060000"
TPREV = "20000131050000"
INFL_MUL = 1.45
BASE = "/work/gv42/v42013/20260923_enkc_convection"
NAMES = {2819: "U", 2820: "V", 3073: "T"}
KEY = {"U": "U [m/s]", "V": "V [m/s]", "T": "T [K]"}
HALF = 30                                          # 図の範囲（観測から ±30 格子 = ±60 km）

cm.use_japanese_font()


def one(exp):
    out = f"{BASE}/sens/{exp}"
    obs = cm.read_obs(f"{out}/../../sens_obs/{exp}/obs_{T}.dat")
    dep = cm.read_obsdep(f"{out}/obsdep/obsdep_{T}.dat")
    lon, lat, Nat = cm.read_global(f"{BASE}/result/{TPREV}/hist/mdet")      # 真値（基準の mdet の 60 分）
    jj, ii, _ = cm.nearest_column(lon, lat, obs[:, 1], obs[:, 2])
    djj, dii, _ = cm.nearest_column(lon, lat, dep[:, 1], dep[:, 2])
    G = physical(cm.read_restart(f"{out}/{T}/gues/mean", T))
    A = physical(cm.read_restart(f"{out}/{T}/anal/mean", T))
    Tr = physical(cm.read_restart(f"{BASE}/result/{T}/anal/mdet", T))

    print(f"=== {exp}: obsdep の観測 {len(dep)} 個（用意した観測 {len(obs)} 個）")
    print("  格子      気圧    O−B      O−A     O−A/O−B 理論値  ばらつき σ_b | d_b      d_a     （真値とのずれ。H は自前の観測演算子）")
    rows = []
    for n in range(len(obs)):
        m = np.flatnonzero((djj == jj[n]) & (dii == ii[n]) & (np.abs(dep[:, 3] - obs[n, 3]) < 0.01))
        name = NAMES[int(obs[n, 0])]
        hn = cm.obs_operator(Nat[name], Nat["PRES"], obs, jj, ii, [n])[0]
        hg = cm.obs_operator(G[KEY[name]], G["P [hPa]"] * 100.0, obs, jj, ii, [n])[0]
        ha = cm.obs_operator(A[KEY[name]], A["P [hPa]"] * 100.0, obs, jj, ii, [n])[0]
        if len(m) != 1:
            print(f"  ({jj[n]:3d}, {ii[n]:3d}) {obs[n, 3]:7.1f}  obsdep にない（QC で捨てられた？）  d_b {hg - hn:+.4f}  d_a {ha - hn:+.4f}")
            continue
        omb, oma, sb = dep[m[0], 9], dep[m[0], 10], dep[m[0], 11]
        th = OBSERR ** 2 / (INFL_MUL * sb ** 2 + OBSERR ** 2)
        rows.append((oma / omb, th))
        print(f"  ({jj[n]:3d}, {ii[n]:3d}) {obs[n, 3]:7.1f}  {omb:+.4f}  {oma:+.4f}  {oma / omb:7.3f}  {th:6.3f}  {sb:.4f}      | "
              f"{hg - hn:+.4f}  {ha - hn:+.4f}")
    if rows:
        r = np.array(rows)
        print(f"  O−A/O−B の平均: 実際 {r[:, 0].mean():.3f}、理論 {r[:, 1].mean():.3f}")

    # まわり: 観測に近い層の修正と必要な修正
    fig, axs = plt.subplots(2, len(obs), figsize=(4.2 * len(obs), 8.2), squeeze=False)
    for n in range(len(obs)):
        name = NAMES[int(obs[n, 0])]
        k = int(np.argmin(np.abs(G["P [hPa]"][:, jj[n], ii[n]] - obs[n, 3])))
        jsel = np.arange(jj[n] - HALF, jj[n] + HALF + 1) % NY
        isel = np.arange(ii[n] - HALF, ii[n] + HALF + 1) % NX
        inc = (A[KEY[name]] - G[KEY[name]])[k][np.ix_(jsel, isel)]
        need = (Tr[KEY[name]] - G[KEY[name]])[k][np.ix_(jsel, isel)]
        vmax = max(np.abs(need).max(), np.abs(inc).max())
        x = (np.arange(-HALF, HALF + 1)) * cm.DX / 1e3
        for row, (f, ttl) in enumerate([(inc, "LETKF の修正（解析 − 第一推定）"), (need, "必要な修正（真値 − 第一推定）")]):
            ax = axs[row, n]
            im = ax.pcolormesh(x, x, f, cmap="RdBu_r", vmin=-vmax, vmax=vmax, shading="nearest")
            ax.plot(0, 0, "k+", ms=12, mew=2)
            ax.add_patch(plt.Circle((0, 0), 20, fill=False, ls="--", color="k", lw=0.8))
            ax.set_aspect("equal")
            ax.set_title(f"({jj[n]}, {ii[n]}) 層 {k + 1} [{obs[n, 3]:.0f} hPa]\n{ttl}", fontsize=9)
            fig.colorbar(im, ax=ax, shrink=0.8, label=f"{name}")
            c = np.corrcoef(inc.ravel(), need.ravel())[0, 1]
            if row == 0:
                ax.text(0.02, 0.02, f"必要な修正との相関 {c:.2f}", transform=ax.transAxes, fontsize=8)
        axs[1, n].set_xlabel("観測からの距離 [km]（破線 = HORI_LOCAL 20 km）")
    fig.suptitle(f"{exp}: 1 点観測（{name}）による修正と、真値との差", fontsize=12, x=0.01, ha="left")
    fig.tight_layout()
    fig.savefig(f"{cm.DOCS}/phase7d/sens/single_obs_{exp}.png", dpi=110)
    print(f"  図: {cm.DOCS}/phase7d/sens/single_obs_{exp}.png")


def main():
    for exp in sys.argv[1:]:
        one(exp)


if __name__ == "__main__":
    main()
