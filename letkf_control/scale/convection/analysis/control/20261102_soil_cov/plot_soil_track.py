#!/usr/bin/env python3
"""土壌水分の動き（2026-11-02）。

初期の摂動は第 1 層だけに入っていて、時間とともに薄まった（docs/control/notes.md）。その動きを 0〜24 時で追う。
1. 目標領域（x 70〜90 km・y 110〜130 km の 20 km 四方。plot_target_prec.py と同じ）の平均: 層ごとの土壌水分、柱の貯水量、
   降水・蒸発・流出（10 分ごと、80 member と mdet）
2. 領域全体: 層ごとの土壌水分の member 間の標準偏差（格子ごとの値の、領域の中央値と 90% 点）と、領域平均（毎正時）
3. 水の収支（mdet と member 平均）: 柱の貯水量の変化 = 降水 − 蒸発 − 流出 の残り（下の層から抜けるぶんなど）を確かめる

- 柱の貯水量 S = Σ_k LAND_WATER_k × Δz_k × 1000 [mm]（Δz = 0.05, 0.15, 0.3, 0.5, 1, 1, 1 m。history の lzh から）
- 蒸発 = LHFLX / 2.5e6 [mm/s]、流出 = LAND_RUNOFF [kg/m²/s = mm/s]、降水 = PREC
- 各 cycle の 1 時間予報の history の 600〜3600 s を使う（0 s は前の cycle の 3600 s と重なるので除く）。1 cycle 目だけ 0 s も使う

使い方: cd analysis && STIME=20000131000000 OUTDIR=… FIGDIR=… python3 control/20261102_soil_cov/plot_soil_track.py [cycle 数（既定 24）] [member 数（既定 80）]
出力: 表（標準出力）と FIGDIR/soil_track_target.png・soil_track_spread.png・soil_budget.png・soil_track.npz
     （2 回目からは npz を読んで図だけ描き直す。作り直すときは消す）
"""
import glob
import os
import sys
from concurrent.futures import ProcessPoolExecutor

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from netCDF4 import Dataset

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))   # analysis/common.py
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "20261102_target"))   # plot_target_prec.py
import common as cm
from common import NX, NY, tstr
from plot_target_prec import DT, I0, J0, K, NT

NCYC = int(sys.argv[1]) if len(sys.argv) > 1 else 24
NMEM = int(sys.argv[2]) if len(sys.argv) > 2 else 80
MEMS = [f"{m:04d}" for m in range(1, NMEM + 1)] + ["mdet"]
NL = 7
LV = 2.5e6                                          # 蒸発の潜熱 [J/kg]
NS = NCYC * NT + 1                                  # 10 分ごとの時刻の数（0 s を含む）
FLX = ["PREC", "LHFLX", "LAND_RUNOFF"]

cm.use_japanese_font()


def read_member(mem):
    """mem の 1. 目標領域の 10 分ごとの値、2. 毎正時の土壌水分の全格子、3. 領域平均の 10 分ごとの値。"""
    tgt = {"W": np.full((NS, NL), np.nan), **{v: np.full(NS, np.nan) for v in FLX}}
    dom = {"W": np.full((NS, NL), np.nan), **{v: np.full(NS, np.nan) for v in FLX}}
    hourly = np.full((NCYC + 1, NL, NY, NX), np.nan, dtype=np.float32)
    dz = None
    for k in range(NCYC):
        d0 = cm.hist_dir(mem, tstr(k))
        files = sorted(glob.glob(f"{d0}/history.pe*.nc"))
        if len(files) != 144:
            sys.exit(f"{d0}: ファイルが {len(files)} 個です。")
        st = {"W": np.zeros((NT + 1, NL)), **{v: np.zeros(NT + 1) for v in FLX}}
        sd = {"W": np.zeros((NT + 1, NL)), **{v: np.zeros(NT + 1) for v in FLX}}
        nt = 0
        for f in files:
            with Dataset(f) as d:
                tt = np.asarray(d.variables["time"][:])
                if not np.allclose(tt, np.arange(0, 3601, DT)):
                    sys.exit(f"{f}: 時刻が足りない（time = {tt}）")
                if dz is None:
                    dz = np.diff(np.asarray(d.variables["lzh"][:]))
                i, j = cm._ij(d)
                w = np.asarray(d.variables["LAND_WATER"][:], dtype=np.float64)          # (時刻, 層, y, x)
                # (時刻, y, x)。LAND_RUNOFF は 0 s が欠損値なので 0 にする（使うのは 1 cycle 目の 0 s だけ）
                a = {v: np.ma.filled(d.variables[v][:].astype(np.float64), 0.0) for v in FLX}
                hourly[k + 1][:, j[:, None], i[None, :]] = w[-1]
                if k == 0:
                    hourly[0][:, j[:, None], i[None, :]] = w[0]
                sd["W"] += w.sum(axis=(2, 3))
                for v in FLX:
                    sd[v] += a[v].sum(axis=(1, 2))
                ii = np.flatnonzero((i >= I0) & (i < I0 + K))
                jj = np.flatnonzero((j >= J0) & (j < J0 + K))
                if ii.size and jj.size:
                    sl = (slice(jj[0], jj[-1] + 1), slice(ii[0], ii[-1] + 1))
                    st["W"] += w[:, :, sl[0], sl[1]].sum(axis=(2, 3))
                    for v in FLX:
                        st[v] += a[v][:, sl[0], sl[1]].sum(axis=(1, 2))
                    nt += ii.size * jj.size
        if nt != K * K:
            sys.exit(f"{d0}: 目標領域の格子が {nt} 個です。")
        s0 = 0 if k == 0 else 1
        for out, s, n in [(tgt, st, K * K), (dom, sd, NX * NY)]:
            for v in out:
                out[v][k * NT + s0:(k + 1) * NT + 1] = s[v][s0:] / n
    return mem, tgt, dom, hourly, dz


def storage(w, dz):
    """層ごとの土壌水分 (..., NL) → 柱の貯水量 [mm]。"""
    return (w * dz).sum(axis=-1) * 1000.0


def main():
    out = cm.figdir()
    cache = f"{out}/soil_track.npz"
    if os.path.exists(cache):
        z = dict(np.load(cache))
    else:
        z = {}
        n = 0
        s1 = s2 = None
        with ProcessPoolExecutor(max_workers=8) as ex:
            for mem, tgt, dom, hourly, dz in ex.map(read_member, MEMS):
                for v in tgt:
                    z[f"{mem}_tgt_{v}"] = tgt[v]
                    z[f"{mem}_dom_{v}"] = dom[v]
                if mem == "mdet":
                    continue
                h = hourly.astype(np.float64)
                s1 = h if s1 is None else s1 + h
                s2 = h ** 2 if s2 is None else s2 + h ** 2
                n += 1
                z["dz"] = dz
        mean = s1 / n
        sdv = np.sqrt(np.maximum(s2 / n - mean ** 2, 0.0))   # 格子ごとの member 間の標準偏差 (時刻, 層, y, x)
        z["sd_med"] = np.median(sdv.reshape(NCYC + 1, NL, -1), axis=2)
        z["sd_p90"] = np.percentile(sdv.reshape(NCYC + 1, NL, -1), 90, axis=2)
        z["sd_tgt"] = sdv[:, :, J0:J0 + K, I0:I0 + K].mean(axis=(2, 3))
        z["mean_dom"] = mean.mean(axis=(2, 3))
        np.savez_compressed(cache, **z)

    dz = z["dz"]
    ens = [m for m in MEMS if m != "mdet"]
    t10 = np.arange(NS) * DT / 3600.0
    th = np.arange(NCYC + 1)

    def get(region, v):
        return np.array([z[f"{m}_{region}_{v}"] for m in ens]), z[f"mdet_{region}_{v}"]

    # ---- 表: 層ごとの member 間の標準偏差（領域の中央値）
    print("土壌水分の member 間の標準偏差 [m³/m³]（毎正時。格子ごとの値の領域の中央値 / 目標領域の平均）")
    print(" 時刻  " + "  ".join(f"第{l + 1}層(中央値/目標)" for l in range(4)))
    for k in th:
        print(f" {k:2d} 時 " + "  ".join(f"{z['sd_med'][k, l]:.4f}/{z['sd_tgt'][k, l]:.4f}    " for l in range(4)))

    # ---- 表: 水の収支（mdet、領域全体と目標領域）
    for region, name in [("dom", "領域全体の平均"), ("tgt", "目標領域の平均")]:
        _, w = get(region, "W")
        _, p = get(region, "PREC")
        _, e = get(region, "LHFLX")
        _, r = get(region, "LAND_RUNOFF")
        S = storage(w, dz)
        cP = np.concatenate([[0], np.cumsum((p[1:] + p[:-1]) / 2 * DT)])
        cE = np.concatenate([[0], np.cumsum((e[1:] + e[:-1]) / 2 / LV * DT)])
        cR = np.concatenate([[0], np.cumsum((r[1:] + r[:-1]) / 2 * DT)])
        z[f"budget_{region}"] = np.array([S - S[0], cP, cE, cR])
        print(f"\n水の収支（mdet、{name}）[mm]（0 時からの積算。残り = 貯水量の変化 − (降水 − 蒸発 − 流出)）")
        print(" 時刻   貯水量の変化   降水     蒸発    流出     残り    | 第1層 第2層 第3層 第4層 [m³/m³]")
        for k in range(0, NCYC + 1, 2):
            s = k * NT
            res = (S[s] - S[0]) - (cP[s] - cE[s] - cR[s])
            print(f" {k:2d} 時  {S[s] - S[0]:8.2f}    {cP[s]:6.2f}  {cE[s]:6.2f}  {cR[s]:6.2f}  {res:7.2f}    | "
                  + " ".join(f"{w[s, l]:.3f}" for l in range(4)))

    # ---- 図 1: 目標領域
    we, wm = get("tgt", "W")
    pe, pm = get("tgt", "PREC")
    fig, axs = plt.subplots(5, 1, figsize=(11, 12.5), sharex=True, constrained_layout=True)
    rows = [(pe * 3600, pm * 3600, "降水強度 [mm/h]", "(a) 降水")] + \
           [(we[:, :, l], wm[:, l], "m³/m³", f"({'bcd'[l]}) 第 {l + 1} 層（{dz[:l].sum() * 100:.0f}〜{dz[:l + 1].sum() * 100:.0f} cm）の土壌水分")
            for l in range(3)] + \
           [(storage(we, dz), storage(wm, dz), "mm", "(e) 柱の貯水量（全 7 層、0〜4 m）")]
    for ax, (e, m, unit, ttl) in zip(axs, rows):
        ax.axvspan(13, 17, color=cm.C3, alpha=0.08, zorder=0, lw=0)
        for row in e:
            ax.plot(t10, row, color=cm.GRAY, lw=0.4, alpha=0.3)
        ax.fill_between(t10, np.percentile(e, 10, axis=0), np.percentile(e, 90, axis=0), color=cm.C1, alpha=0.25, lw=0,
                        label="member の 10〜90%")
        ax.plot(t10, e.mean(axis=0), color=cm.C1, lw=1.6, label=f"member 平均（{len(e)}）")
        ax.plot(t10, m, color="k", lw=1.6, label="mdet")
        ax.set_ylabel(unit)
        ax.set_title(ttl, loc="left", fontsize=11)
        ax.grid(alpha=0.3)
    axs[0].legend(frameon=False, loc="upper left", fontsize=8, ncol=3)
    axs[-1].set_xlabel("STIME からの時間 [h]（薄い赤: 目標領域の雨のイベント 13〜17 時）")
    axs[-1].set_xlim(0, NCYC)
    axs[-1].set_xticks(np.arange(0, NCYC + 1, 2))
    fig.suptitle(f"目標領域（x {I0 * 2}〜{(I0 + K) * 2} km・y {J0 * 2}〜{(J0 + K) * 2} km）の土壌水分", fontsize=12, x=0.01, ha="left")
    fig.savefig(f"{out}/soil_track_target.png", dpi=110)

    # ---- 図 2: member 間のばらつき（層ごと）
    fig, axs = plt.subplots(1, 2, figsize=(13, 4.8), constrained_layout=True)
    cols = plt.get_cmap("viridis", NL)
    for l in range(NL):
        lab = f"第 {l + 1} 層（{dz[:l].sum() * 100:.0f}〜{dz[:l + 1].sum() * 100:.0f} cm）"
        axs[0].plot(th, z["sd_med"][:, l], color=cols(l), lw=1.6, marker="o", ms=3, label=lab)
        axs[1].plot(th, z["sd_p90"][:, l], color=cols(l), lw=1.6, marker="o", ms=3, label=lab)
    for ax, ttl in zip(axs, ["(a) 格子ごとの標準偏差の、領域の中央値", "(b) 格子ごとの標準偏差の、領域の 90% 点"]):
        ax.set_yscale("log")
        ax.set_ylim(1e-5, 0.1)
        ax.set_xlim(0, NCYC)
        ax.set_xticks(np.arange(0, NCYC + 1, 2))
        ax.set_xlabel("STIME からの時間 [h]")
        ax.set_ylabel("member 間の標準偏差 [m³/m³]")
        ax.set_title(ttl, loc="left", fontsize=11)
        ax.grid(alpha=0.3, which="both")
    axs[0].axhline(0.01 / np.sqrt(3), color="0.5", ls="--", lw=1)
    axs[0].text(0.3, 0.01 / np.sqrt(3) * 1.15, "初期の摂動（第 1 層、0.0058）", fontsize=8, color="0.4")
    axs[1].legend(frameon=False, fontsize=8, loc="lower right")
    fig.suptitle(f"土壌水分の member 間のばらつき（{len(ens)} member、毎正時）", fontsize=12, x=0.01, ha="left")
    fig.savefig(f"{out}/soil_track_spread.png", dpi=110)

    # ---- 図 3: 水の収支（mdet）
    fig, axs = plt.subplots(1, 2, figsize=(13, 4.6), constrained_layout=True)
    for ax, region, name in [(axs[0], "dom", "(a) 領域全体の平均"), (axs[1], "tgt", "(b) 目標領域の平均")]:
        dS, cP, cE, cR = z[f"budget_{region}"]
        ax.plot(t10, cP, color=cm.C1, lw=1.6, label="降水（積算）")
        ax.plot(t10, -cE, color=cm.C2, lw=1.6, label="− 蒸発（積算）")
        ax.plot(t10, -cR, color=cm.C3, lw=1.6, label="− 流出（積算）")
        ax.plot(t10, dS, color="k", lw=1.8, label="貯水量の変化")
        ax.plot(t10, dS - (cP - cE - cR), color="k", lw=1.0, ls=":", label="残り")
        ax.axhline(0, color="0.5", lw=0.8)
        ax.set_xlim(0, NCYC)
        ax.set_xticks(np.arange(0, NCYC + 1, 2))
        ax.set_xlabel("STIME からの時間 [h]")
        ax.set_ylabel("0 時からの積算 [mm]")
        ax.set_title(name, loc="left", fontsize=11)
        ax.grid(alpha=0.3)
    axs[0].legend(frameon=False, fontsize=8)
    fig.suptitle("土壌の水の収支（mdet）", fontsize=12, x=0.01, ha="left")
    fig.savefig(f"{out}/soil_budget.png", dpi=110)
    print(f"\n図: {out}/soil_track_target.png, soil_track_spread.png, soil_budget.png")


if __name__ == "__main__":
    main()
