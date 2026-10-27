#!/usr/bin/env python3
"""B-2（Phase 7d「終了の基準」の案）: 誤差をスケール（水平の波長）に分けて、同化あり・なしを比べる。

各実験・各解析時刻（1 時間ごと）で、第一推定の平均 − 真値・解析の平均 − 真値 の場を、層ごとに水平方向に 2 次元フーリエ変換し
（領域は二重周期）、波長の帯ごとの分散（パーセバルの等式で、帯の分散を足すと全体の分散になる）から RMSE を出す。
帯: 32 km 以上 / 16〜32 km / 8〜16 km / 8 km 未満（8 km = 観測の間隔、16〜32 km ≈ HORI_LOCAL 10〜20 km の影響の範囲）。
平均（波数 0）の成分は 32 km 以上の帯に入れる。

読むもの: <OUTDIR>/<t>/{gues_letkf,gues}/mean・anal/mean（各実験）、<TRUTHDIR>/<t>/{gues,anal}/mdet（真値）
出力: 表（標準出力）と FIGDIR/scales_<組>.png・scales_<組>.npz
使い方: STIME=20000131000000 FIGDIR=… python3 check_scales.py <組の名前> <真値の場所> <実験名>[=<結果の場所>] ...
        図だけ描き直す: FIGDIR=… python3 check_scales.py --plot <組の名前>（FIGDIR/scales_<組>.npz を読む）
  例:  python3 check_scales.py short /work/gv42/v42013/20260923_enkc_convection/result Cp L10 M40L10 M80L10 NoDA
       （<結果の場所> を省くと /work/gv42/v42013/20260923_enkc_convection/sens/<実験名>）
"""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import common as cm
from common import NX, NY, physical, tstr

BANDS = [("32 km 以上", 32.0, np.inf), ("16〜32 km", 16.0, 32.0), ("8〜16 km", 8.0, 16.0), ("8 km 未満", 0.0, 8.0)]
KEYS = ["U [m/s]", "T [K]", "QV [g/kg]", "W [m/s]"]
SENS = "/work/gv42/v42013/20260923_enkc_convection/sens"

cm.use_japanese_font()


def band_masks():
    """(NY, NX) の波数ごとに、どの帯に入るか。波長 = 領域の長さ / |波数|。"""
    L = NX * cm.DX / 1e3                           # 240 km
    kx = np.fft.fftfreq(NX, 1.0 / NX)
    ky = np.fft.fftfreq(NY, 1.0 / NY)
    kk = np.hypot(*np.meshgrid(ky, kx, indexing="ij"))
    lam = np.where(kk > 0, L / np.maximum(kk, 1e-12), np.inf)
    return [(lam >= lo) & (lam < hi) for _, lo, hi in BANDS]


MASKS = band_masks()


def band_rmse(e):
    """誤差の場 e（NZ, NY, NX）の、帯ごとの RMSE（全格子点で平均した値）。"""
    f = np.fft.fft2(e, axes=(1, 2))
    p = (np.abs(f) ** 2).sum(axis=0) / (e.size * NX * NY)        # パーセバル: 全体の平均二乗 = Σ |F|² / (N · NX NY)
    return np.array([np.sqrt(p[m].sum()) for m in MASKS])


def first(*paths):
    for p in paths:
        if os.path.isdir(p) and any(f.endswith(".nc") for f in os.listdir(p)):
            return p
    raise FileNotFoundError(paths)


def plot(group, exps, res, times, out):
    hrs = np.arange(1, len(times) + 1)
    pal = ["k", cm.C1, cm.C3, cm.C2, "#7d3c98", "#b5651d"]
    fig, axs = plt.subplots(3, len(BANDS), figsize=(4.4 * len(BANDS), 3.4 * 3), squeeze=False)
    for i, key in enumerate(KEYS[:3]):
        for j, (bname, _, _) in enumerate(BANDS):
            ax = axs[i, j]
            for n, e in enumerate(exps):
                if "NoDA" in e:
                    ax.plot(hrs, res[e]["a"][:, i, j], "-.", color=cm.GRAY, marker="o", ms=3, label=e)
                else:
                    ax.plot(hrs, res[e]["a"][:, i, j], "-", color=pal[n % len(pal)], marker="o", ms=3, label=e)
            ax.set_title(f"{key}: 波長 {bname}", fontsize=10, loc="left")
            ax.set_ylim(bottom=0)
            ax.grid(alpha=0.3)
            if i == 2:
                ax.set_xlabel("解析時刻（開始からの時間）[h]")
        axs[i, 0].set_ylabel(f"解析の RMSE [{key.split('[')[1].rstrip(']')}]")
    axs[0, 0].legend(fontsize=8, frameon=False)
    fig.suptitle("スケール（水平の波長）ごとの解析の誤差。灰色の一点鎖線 = 同化なし。観測は 8 km おき", fontsize=12, x=0.01, ha="left")
    fig.tight_layout()
    fig.savefig(f"{out}/scales_{group}.png", dpi=110)
    print(f"\n図: {out}/scales_{group}.png")


def main():
    if sys.argv[1] == "--plot":
        group = sys.argv[2]
        out = cm.figdir()
        z = np.load(f"{out}/scales_{group}.npz")
        exps = sorted({k.rsplit("_", 1)[0] for k in z.files if k.endswith("_a")}, key=lambda e: list(z.files).index(f"{e}_g"))
        res = {e: {x: z[f"{e}_{x}"] for x in ["g", "a", "tot"]} for e in exps}
        plot(group, exps, res, z["times"], out)
        return
    group, truth = sys.argv[1], sys.argv[2]
    exps = []
    for a in sys.argv[3:]:
        name, _, path = a.partition("=")
        exps.append((name, path or f"{SENS}/{name}"))
    res = {e: {"g": [], "a": [], "tot": []} for e, _ in exps}
    k = 1
    times = []
    while True:
        t = tstr(k)
        if not all(os.path.isdir(f"{p}/{t}/anal/mean") for _, p in exps):
            break
        T = physical(cm.read_restart(first(f"{truth}/{t}/gues/mdet", f"{truth}/{t}/anal/mdet"), t))
        print(f"--- 解析時刻 {t}（{k} 時間目）")
        for e, p in exps:
            G = physical(cm.read_restart(first(f"{p}/{t}/gues_letkf/mean", f"{p}/{t}/gues/mean"), t))
            A = physical(cm.read_restart(f"{p}/{t}/anal/mean", t))
            rg = np.array([band_rmse(G[key] - T[key]) for key in KEYS])     # (変数, 帯)
            ra = np.array([band_rmse(A[key] - T[key]) for key in KEYS])
            res[e]["g"].append(rg)
            res[e]["a"].append(ra)
            res[e]["tot"].append([cm.rms(A[key] - T[key]) for key in KEYS])
            print(f"   {e:10s} " + "  ".join(
                f"{key.split()[0]}: " + " ".join(f"{b:.3f}→{a:.3f}" for b, a in zip(rg[i], ra[i])) for i, key in enumerate(KEYS[:2])))
        times.append(t)
        k += 1
        sys.stdout.flush()
    if not times:
        sys.exit("解析時刻が見つかりません。")
    for e in res:
        for x in res[e]:
            res[e][x] = np.array(res[e][x])                             # (時刻, 変数, 帯)

    ref = exps[-1][0] if "NoDA" in exps[-1][0] else None
    print("\n解析の RMSE（帯ごと、最後の 3 時刻の平均）" + (f"。かっこ内は {ref} に対する比" if ref else ""))
    print(f"   {'実験':10s} {'変数':5s} " + " ".join(f"{b[0]:>14s}" for b in BANDS))
    for e, _ in exps:
        for i, key in enumerate(KEYS):
            v = res[e]["a"][-3:, i].mean(0)
            r = res[ref]["a"][-3:, i].mean(0) if ref else None
            print(f"   {e:10s} {key.split()[0]:5s} " + " ".join(
                f"{x:7.4f}" + (f"({x / y:5.2f})" if ref else "       ") for x, y in zip(v, r if ref else v)))
    print("\n誤差の分散の帯ごとの割合（第一推定、最後の時刻、最初の実験）: " + "  ".join(
        f"{key.split()[0]}: " + " ".join(f"{(x ** 2) / (res[exps[0][0]]['g'][-1, i] ** 2).sum() * 100:.0f}%"
                                          for x in res[exps[0][0]]["g"][-1, i]) for i, key in enumerate(KEYS)))

    out = cm.figdir()
    np.savez(f"{out}/scales_{group}.npz", times=np.array(times), keys=np.array(KEYS), bands=np.array([b[0] for b in BANDS]),
             **{f"{e}_{x}": res[e][x] for e in res for x in res[e]})
    plot(group, [e for e, _ in exps], res, times, out)


if __name__ == "__main__":
    main()
