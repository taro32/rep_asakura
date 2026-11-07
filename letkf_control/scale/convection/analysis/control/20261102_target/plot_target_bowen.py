#!/usr/bin/env python3
"""制御の目標領域（x = 80 km・y = 120 km を中心とする 20 km 四方）の地表フラックス・ボーエン比・境界層の高さの時間変化（2026-11-02）。

介入のシグナルの候補としてボーエン比を見る。降水（plot_target_prec.py と同じ量）と並べ、雨の前に動くかを確かめる。
- 目標領域・読むファイルは plot_target_prec.py と同じ（target_files）
- 各 cycle の 1 時間予報の history の 600〜3600 s（10 分ごとの瞬間値）を目標領域で平均する
- ボーエン比 = 顕熱 SHFLX の平均 / 潜熱 LHFLX の平均（格子ごとの比の平均ではない）
- 比べるため、mdet の領域全体の平均も描く（全 144 ファイルを読む）

使い方: cd analysis && STIME=20000131000000 OUTDIR=… FIGDIR=… python3 control/20261102_target/plot_target_bowen.py [cycle 数（既定 24）] [member 数（既定 80）]
出力: 表（標準出力）と FIGDIR/target_bowen.png・target_bowen.npz（2 回目からは npz を読んで図だけ描き直す。作り直すときは消す）
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
import common as cm
from common import tstr
from plot_target_prec import DT, I0, J0, K, NT, target_files

NCYC = int(sys.argv[1]) if len(sys.argv) > 1 else 24
NMEM = int(sys.argv[2]) if len(sys.argv) > 2 else 80
MEMS = [f"{m:04d}" for m in range(1, NMEM + 1)] + ["mdet"]
VARS = ["PREC", "SHFLX", "LHFLX", "PBLH"]

cm.use_japanese_font()


def series(args):
    """mem の目標領域（sel）の平均を、変数ごとに 10 分ごと NCYC × NT 個。PREC は mm/h にする。"""
    mem, sel = args
    out = {v: np.full(NCYC * NT, np.nan) for v in VARS}
    for k in range(NCYC):
        d0 = cm.hist_dir(mem, tstr(k))
        s = {v: np.zeros(NT + 1) for v in VARS}
        n = 0
        for name, ii, jj in sel:
            with Dataset(f"{d0}/{name}") as d:
                tt = np.asarray(d.variables["time"][:])
                if not np.allclose(tt, np.arange(0, 3601, DT)):
                    sys.exit(f"{mem} の {tstr(k)} の history の時刻が足りない（time = {tt}）")
                for v in VARS:
                    s[v] += np.asarray(d.variables[v][:, jj[0]:jj[-1] + 1, ii[0]:ii[-1] + 1], dtype=np.float64).sum(axis=(1, 2))
            n += len(ii) * len(jj)
        for v in VARS:
            out[v][k * NT:(k + 1) * NT] = s[v][1:] / n
    out["PREC"] *= 3600.0
    return mem, out


def all_files(mem):
    """mem の全ファイル（領域全体の平均用）。"""
    sel = []
    for f in sorted(glob.glob(f"{cm.hist_dir(mem, tstr(0))}/history.pe*.nc")):
        with Dataset(f) as d:
            i, j = cm._ij(d)
        sel.append((os.path.basename(f), np.arange(len(i)), np.arange(len(j))))
    return sel


def main():
    out = cm.figdir()
    cache = f"{out}/target_bowen.npz"
    if os.path.exists(cache):
        z = np.load(cache)
        r = {m: {v: z[f"{m}_{v}"] for v in VARS} for m in MEMS + ["mdet_domain"]}
    else:
        sel = target_files()
        jobs = [(m, sel) for m in MEMS] + [("mdet", all_files("mdet"))]
        with ProcessPoolExecutor(max_workers=8) as ex:
            res = list(ex.map(series, jobs))
        r = {m: o for m, o in res[:-1]}
        r["mdet_domain"] = res[-1][1]
        np.savez_compressed(cache, **{f"{m}_{v}": r[m][v] for m in r for v in VARS})

    ens = {v: np.array([r[m][v] for m in MEMS[:-1]]) for v in VARS}
    ens["BOWEN"] = ens["SHFLX"] / ens["LHFLX"]
    for m in ("mdet", "mdet_domain"):
        r[m]["BOWEN"] = r[m]["SHFLX"] / r[m]["LHFLX"]
    md, dom = r["mdet"], r["mdet_domain"]
    t10 = (np.arange(NCYC * NT) + 1) * DT / 3600.0

    def hourly(a):
        return a.reshape(*a.shape[:-1], NCYC, NT).mean(axis=-1)

    print(f"目標領域: x {I0 * 2}〜{(I0 + K) * 2} km・y {J0 * 2}〜{(J0 + K) * 2} km の平均（1 時間の平均）。"
          "ボーエン比は 1 時間平均の顕熱 / 潜熱。「領域」は mdet の領域全体の平均")
    print(" 時間    降水[mm]       顕熱[W/m2]          潜熱[W/m2]          ボーエン比           境界層の高さ[m]")
    print("        mdet  平均    mdet  平均  領域    mdet  平均  領域    mdet  平均  領域    mdet   平均   領域")
    h = {v: (hourly(md[v]), hourly(ens[v]).mean(axis=0), hourly(dom[v])) for v in VARS}
    hb = (h["SHFLX"][0] / h["LHFLX"][0], (hourly(ens["SHFLX"]) / hourly(ens["LHFLX"])).mean(axis=0), h["SHFLX"][2] / h["LHFLX"][2])
    for k in range(NCYC):
        print(f" {k:2d}-{k + 1:2d}  {h['PREC'][0][k]:5.2f} {h['PREC'][1][k]:5.2f}  "
              f"{h['SHFLX'][0][k]:6.1f}{h['SHFLX'][1][k]:6.1f}{h['SHFLX'][2][k]:6.1f}  "
              f"{h['LHFLX'][0][k]:6.1f}{h['LHFLX'][1][k]:6.1f}{h['LHFLX'][2][k]:6.1f}  "
              f"{hb[0][k]:6.3f}{hb[1][k]:6.3f}{hb[2][k]:6.3f}  "
              f"{h['PBLH'][0][k]:6.0f} {h['PBLH'][1][k]:6.0f} {h['PBLH'][2][k]:6.0f}")

    panels = [("PREC", "降水強度 [mm/h]", "(a) 降水"),
              ("SHFLX", "顕熱 [W/m²]", "(b) 顕熱フラックス"),
              ("LHFLX", "潜熱 [W/m²]", "(c) 潜熱フラックス"),
              ("BOWEN", "ボーエン比", "(d) ボーエン比（顕熱の平均 / 潜熱の平均）"),
              ("PBLH", "境界層の高さ [m]", "(e) 境界層の高さ")]
    fig, axs = plt.subplots(len(panels), 1, figsize=(11, 13), sharex=True, constrained_layout=True)
    for ax, (v, unit, ttl) in zip(axs, panels):
        ax.axvspan(0, 7, color="0.92", zorder=0, lw=0)
        ax.axvspan(13, 17, color=cm.C3, alpha=0.08, zorder=0, lw=0)
        e = ens[v]
        for row in e:
            ax.plot(t10, row, color=cm.GRAY, lw=0.4, alpha=0.3)
        ax.fill_between(t10, np.nanpercentile(e, 10, axis=0), np.nanpercentile(e, 90, axis=0), color=cm.C1, alpha=0.25, lw=0,
                        label="member の 10〜90%")
        ax.plot(t10, np.nanmean(e, axis=0), color=cm.C1, lw=1.6, label=f"member 平均（{len(e)}）")
        ax.plot(t10, md[v], color="k", lw=1.6, label="mdet（現実の側）")
        if v != "PREC":
            ax.plot(t10, dom[v], color="k", lw=1.0, ls="--", label="mdet の領域全体の平均")
        ax.set_ylabel(unit)
        ax.set_title(ttl, loc="left", fontsize=11)
        ax.grid(alpha=0.3)
    axs[0].set_ylim(bottom=0)
    axs[1].legend(frameon=False, loc="upper left", fontsize=8, ncol=4)
    axs[-1].set_xlabel("STIME からの時間 [h]（灰: 同化の誤差が横ばいになる前、薄い赤: 目標領域の雨のイベント 13〜17 時）")
    axs[-1].set_xlim(0, NCYC)
    axs[-1].set_xticks(np.arange(0, NCYC + 1, 2))
    fig.suptitle(f"制御の目標領域（x {I0 * 2}〜{(I0 + K) * 2} km・y {J0 * 2}〜{(J0 + K) * 2} km、20 km 四方）の地表フラックスとボーエン比",
                 fontsize=12, x=0.01, ha="left")
    fig.savefig(f"{out}/target_bowen.png", dpi=110)
    print(f"図: {out}/target_bowen.png")


if __name__ == "__main__":
    main()
