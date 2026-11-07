#!/usr/bin/env python3
"""パッチ型の土壌水分の摂動を入れたアンサンブル予報の解析（2026-11-03）。

control/20261103_patch_fcst/make_patch_fcst.py で作り、8 時から 18 時まで同化なしで予報した 80 member（0001〜0080）と mdet（0081）。
member には 20 km 四方のパッチごとの土壌水分の摂動（標準偏差 0.02、0〜20 cm）が入っている。目標領域はちょうど 1 つのパッチ。
見るもの:
1. 目標領域の降水・顕熱・潜熱・ボーエン比・境界層の高さの時系列（80 member と mdet）。Phase 8（同じ時刻）とも比べる
2. 目標領域のパッチの摂動 u と、目標領域の雨 Y（13〜17 時の合計・15〜16 時）・ボーエン比・境界層の高さの相関（時刻ごと）
3. 144 個のパッチそれぞれの摂動と Y の相関の地図（どこを湿らせた member で雨が少ないか）

使い方: cd analysis && FIGDIR=… python3 control/20261103_patch_fcst/check_patch_fcst.py [実験の場所（既定 …/phase9_patch_t08）]
出力: 表（標準出力）と FIGDIR/patch_target.png・patch_corr.png・patch_map.png・patch_fcst.npz
     （2 回目からは npz を読んで図だけ描き直す。作り直すときは消す）
"""
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Rectangle
from netCDF4 import Dataset

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))   # analysis/common.py
import common as cm
from common import DX, NX, NY

EXP = sys.argv[1] if len(sys.argv) > 1 else "/work/gv42/v42013/20260923_enkc_convection/phase9_patch_t08"
T0 = 8                                              # 予報の開始時刻 [h]（STIME から）
I0, J0, K = 35, 55, 10                              # 目標領域（0 始まり）
DT = 600.0
VARS = ["PREC", "SHFLX", "LHFLX", "PBLH", "LAND_WATER"]
RC = 0.22
NPERM = 1000

cm.use_japanese_font()


def series(mem):
    """mem の目標領域の平均（10 分ごと、0 s〜）。LAND_WATER は第 1・2 層の 0〜20 cm の平均。"""
    out = {}
    n = 0
    for f in sorted(os.listdir(f"{EXP}/hist/{mem}")):
        with Dataset(f"{EXP}/hist/{mem}/{f}") as d:
            i, j = cm._ij(d)
            ii = np.flatnonzero((i >= I0) & (i < I0 + K))
            jj = np.flatnonzero((j >= J0) & (j < J0 + K))
            if not (ii.size and jj.size):
                continue
            sl = (slice(jj[0], jj[-1] + 1), slice(ii[0], ii[-1] + 1))
            for v in VARS:
                a = np.asarray(np.ma.filled(d.variables[v][:].astype(np.float64), np.nan))
                if v == "LAND_WATER":
                    a = (a[:, 0] * 0.05 + a[:, 1] * 0.15) / 0.2
                s = a[:, sl[0], sl[1]].sum(axis=(1, 2))
                out[v] = out.get(v, 0) + s
            n += ii.size * jj.size
    if n != K * K:
        sys.exit(f"{mem}: 目標領域の格子が {n} 個です。")
    out = {v: out[v] / n for v in VARS}
    out["PREC"] = out["PREC"] * 3600.0
    return mem, out


def corr(a, y):
    """a（member, ...）と y（member）の相関。"""
    aa = a - a.mean(axis=0)
    ya = y - y.mean()
    return np.tensordot(ya, aa, axes=(0, 0)) / np.sqrt((aa ** 2).sum(axis=0) * (ya ** 2).sum())


def main():
    out = cm.figdir()
    cache = f"{out}/patch_fcst.npz"
    pz = np.load(f"{EXP}/perturbation.npz")
    det = str(pz["mdet"])
    mems = [f"{k:04d}" for k in range(1, int(det))]
    if os.path.exists(cache):
        z = dict(np.load(cache))
        r = {m: {v: z[f"{m}_{v}"] for v in VARS} for m in mems + [det]}
    else:
        with ProcessPoolExecutor(max_workers=8) as ex:
            r = dict(ex.map(series, mems + [det]))
        np.savez_compressed(cache, **{f"{m}_{v}": r[m][v] for m in r for v in VARS})

    nt = len(r[det]["PREC"])
    t = T0 + np.arange(nt) * DT / 3600.0
    E = {v: np.array([r[m][v] for m in mems]) for v in VARS}
    E["BOWEN"] = E["SHFLX"] / E["LHFLX"]
    md = dict(r[det]); md["BOWEN"] = md["SHFLX"] / md["LHFLX"]

    def hourly_rain(p):                               # p: (..., nt) [mm/h]、0 s から。k 時〜k+1 時の量 [mm]
        q = p[..., 1:].reshape(*p.shape[:-1], -1, 6).mean(axis=-1)
        return q                                      # 列 h = T0 + h 時〜T0 + h + 1 時
    hr = hourly_rain(E["PREC"]); hm = hourly_rain(md["PREC"])
    Y = {"total": (hr[:, 13 - T0:17 - T0].sum(axis=1), "13〜17 時の合計"), "peak": (hr[:, 15 - T0], "15〜16 時")}
    ym = {"total": hm[13 - T0:17 - T0].sum(), "peak": hm[15 - T0]}

    # 摂動（第 1 層、実際の差）をパッチごとに平均 → (member, 12, 12)。パッチ (pj, pi) は格子 j = OFFSET + 10 pj …
    off, P = int(pz["offset"]), int(pz["patch"])
    U = np.array([np.roll(np.roll(pz[m], -off, 0), -off, 1).reshape(NY // P, P, NX // P, P).mean(axis=(1, 3)) for m in mems])
    pj_t, pi_t = (J0 - off) // P, (I0 - off) // P
    u = U[:, pj_t, pi_t]                              # 目標領域のパッチの摂動

    print(f"実験: {EXP}（member {len(mems)}、mdet = {det}）")
    print(f"目標領域のパッチの摂動 u: 平均 {u.mean():+.4f}、標準偏差 {u.std():.4f} m³/m³")
    for key, (y, lab) in Y.items():
        print(f"Y（{lab}）: member 平均 {y.mean():.2f}、標準偏差 {y.std():.2f}、範囲 {y.min():.2f}〜{y.max():.2f} mm、mdet {ym[key]:.2f} mm")
    rng = np.random.default_rng(0)
    print("\n目標領域のパッチの摂動 u と各量の相関（|r| > 0.22 が 80 member の 5%）")
    for key, (y, lab) in Y.items():
        rr = np.corrcoef(u, y)[0, 1]
        perm = np.array([abs(np.corrcoef(u, rng.permutation(y))[0, 1]) for _ in range(NPERM)])
        slope = np.polyfit(u, y, 1)[0]
        print(f"  Y = {lab}: r = {rr:+.2f}（並べ替えで |r| 以上になる割合 {(perm >= abs(rr)).mean():.3f}）、"
              f"傾き {slope:+.0f} mm/(m³/m³)（0.01 湿らせると {slope * 0.01:+.2f} mm）")
    print("  時刻ごと（1 時間平均）: 0〜20 cm の土壌水分 / 潜熱 / ボーエン比 / 境界層の高さ / 降水 との相関")
    hv = {v: E[v][:, 1:].reshape(len(mems), -1, 6).mean(axis=2) for v in ["LAND_WATER", "LHFLX", "BOWEN", "PBLH", "PREC"]}
    for h in range(hv["PREC"].shape[1]):
        print(f"   {T0 + h:2d}〜{T0 + h + 1:2d} 時: " + "  ".join(f"{v} {np.corrcoef(u, hv[v][:, h])[0, 1]:+.2f}" for v in hv))

    # ---- 図 1: 目標領域の時系列
    panels = [("PREC", "降水強度 [mm/h]"), ("LHFLX", "潜熱 [W/m²]"), ("BOWEN", "ボーエン比"), ("PBLH", "境界層の高さ [m]"),
              ("LAND_WATER", "土壌水分 0〜20 cm [m³/m³]")]
    fig, axs = plt.subplots(len(panels), 1, figsize=(11, 13), sharex=True, constrained_layout=True)
    wet = u > np.median(u)
    for ax, (v, lab) in zip(axs, panels):
        ax.axvspan(13, 17, color=cm.C3, alpha=0.08, lw=0)
        for row, w in zip(E[v], wet):
            ax.plot(t, row, color=cm.C1 if w else cm.C2, lw=0.4, alpha=0.35)
        ax.plot(t, np.nanmean(E[v][wet], axis=0), color=cm.C1, lw=1.8, label="目標のパッチを湿らせた半分の平均")
        ax.plot(t, np.nanmean(E[v][~wet], axis=0), color=cm.C2, lw=1.8, label="目標のパッチを乾かした半分の平均")
        ax.plot(t, md[v], color="k", lw=1.6, label="mdet（摂動なし）")
        ax.set_ylabel(lab)
        ax.grid(alpha=0.3)
    axs[0].legend(frameon=False, fontsize=8, ncol=3, loc="upper left")
    axs[-1].set_xlabel("STIME からの時間 [h]（8 時から同化なしで予報。薄い赤: 13〜17 時）")
    axs[-1].set_xlim(T0, t[-1])
    fig.suptitle("目標領域（20 km 四方）の時系列。member を、目標のパッチの摂動の正負（中央値の上下）で色分け", fontsize=12, x=0.01, ha="left")
    fig.savefig(f"{out}/patch_target.png", dpi=110)

    # ---- 図 2: u と Y の散布図
    fig, axs = plt.subplots(1, 2, figsize=(12, 4.8), constrained_layout=True)
    for ax, (key, (y, lab)) in zip(axs, Y.items()):
        ax.scatter(u * 100, y, s=14, color=cm.C1)
        ax.axhline(ym[key], color="k", ls="--", lw=1, label=f"mdet（{ym[key]:.1f} mm）")
        c = np.polyfit(u, y, 1)
        xx = np.linspace(u.min(), u.max(), 2)
        ax.plot(xx * 100, np.polyval(c, xx), color="0.4", lw=1)
        ax.set_xlabel("目標のパッチの摂動 [10⁻² m³/m³]")
        ax.set_ylabel(f"目標領域の雨（{lab}）[mm]")
        ax.set_title(f"r = {np.corrcoef(u, y)[0, 1]:+.2f}", loc="left", fontsize=11)
        ax.grid(alpha=0.3)
        ax.legend(frameon=False, fontsize=9)
    fig.suptitle("目標のパッチの土壌水分の摂動と、目標領域の雨（80 member）", fontsize=12, x=0.01, ha="left")
    fig.savefig(f"{out}/patch_corr.png", dpi=110)

    # ---- 図 3: パッチごとの摂動と Y の相関の地図
    fig, axs = plt.subplots(1, 2, figsize=(12, 5.4), constrained_layout=True)
    for ax, (key, (y, lab)) in zip(axs, Y.items()):
        c = corr(U, y)                                # (12, 12)
        frac = (np.abs(c) > RC).mean()
        perm = np.array([(np.abs(corr(U, rng.permutation(y))) > RC).mean() for _ in range(NPERM)])
        full = np.zeros((NY, NX))
        full[:] = c[(((np.arange(NY) - off) % NY) // P)[:, None], (((np.arange(NX) - off) % NX) // P)[None, :]]
        im = ax.imshow(full, origin="lower", extent=[0, NX * DX / 1e3, 0, NY * DX / 1e3], cmap="RdBu_r", vmin=-0.5, vmax=0.5)
        ax.add_patch(Rectangle((I0 * DX / 1e3, J0 * DX / 1e3), K * DX / 1e3, K * DX / 1e3, fill=False, ec="k", lw=1.5))
        ax.set_title(f"Y = {lab}（|r| > {RC} のパッチ {frac * 100:.0f}%、偶然なら ≤ {np.percentile(perm, 95) * 100:.0f}%）",
                     loc="left", fontsize=10)
        ax.set_xlabel("x [km]")
        ax.set_ylabel("y [km]")
        print(f"\nパッチごとの相関（Y = {lab}）: |r| > {RC} のパッチ {frac * 100:.1f}%（偶然の 95% 点 {np.percentile(perm, 95) * 100:.1f}%）、"
              f"目標のパッチ {c[pj_t, pi_t]:+.2f}、最小 {c.min():+.2f}、最大 {c.max():+.2f}")
    fig.colorbar(im, ax=axs, shrink=0.8, label="相関 r（負 = そのパッチを湿らせた member ほど目標領域の雨が少ない）")
    fig.suptitle("各パッチ（20 km 四方）の土壌水分の摂動と、目標領域（黒枠）の雨の相関", fontsize=12, x=0.01, ha="left")
    fig.savefig(f"{out}/patch_map.png", dpi=110)
    print(f"\n図: {out}/patch_target.png, patch_corr.png, patch_map.png")


if __name__ == "__main__":
    main()
