#!/usr/bin/env python3
"""Phase 7d の 1 cycle（ジョブ 9829615、土壌水分摂動の初期値）の結果を、ミーティング用の図にまとめる。

数値は check_truth.py・check_members.py と同じ定義。
- fig1_ensemble.png: 誤差の大きさ（観測誤差との比較）と、誤差 / ばらつき（前回の初期値との比較）
- fig2_effect.png:   解析 / 第一推定 の RMSE 比（全体・観測の柱・観測の間）と、観測の柱からの距離ごとの比
- fig3_zoom.png:     U の 1 層を拡大し、「必要な修正」「LETKF の修正」「残った誤差」を並べる。修正量の散布図
- fig4_growth.png:   0〜60 分のばらつきの育ち方（U・降水・最上層の土壌水分）

計算結果は OUTDIR/plot_1cycle_cache.npz に保存し、2 回目からは図だけ描き直す（作り直すときは消す）。

使い方（退避した結果を読む）:
  cd analysis && STIME=20000131000000 OUTDIR=/work/gv42/v42013/20260923_enkc_convection/result/bak_soil_1cycle_9829615 python3 plot_1cycle.py
図は docs/phase7d/run_soil_1cycle/ に出る（この実行の記録の場所に固定）。
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import common as cm
from common import C1, C2, C3, GRAY, NX, NY, OBSERR, physical, physical_sprd, rms

OUT = f"{cm.DOCS}/phase7d/run_soil_1cycle"
CACHE = f"{cm.OUTDIR}/plot_1cycle_cache.npz"
LEV = 13                                           # U の地図の層（0 始まり。第一推定の U の RMSE が最大の層 14）
ZOOM = (slice(10, 56), slice(10, 61))              # 拡大する範囲（j, i）= y 20〜110 km、x 20〜120 km
# 前回（1/1 開始・水蒸気摂動の初期値）の RMSE / ばらつき（docs/phase7/phase7_notes.md）
PREV = {"U [m/s]": 0.66, "V [m/s]": 0.66, "W [m/s]": 0.35, "T [K]": 0.81,
        "P [hPa]": 0.36, "QV [g/kg]": 0.79, "QHYD [g/kg]": 0.49}
# 観測の柱からの距離（4 格子おきの格子の中で、x・y のずれ 0〜2 格子の組）
DCLS = [(0, 0), (0, 1), (1, 1), (0, 2), (1, 2), (2, 2)]

cm.use_japanese_font()


def offset_class():
    """各柱の、最も近い観測の柱からの x・y のずれ（0〜2 格子、小さいほうを先）。"""
    d = np.minimum(np.arange(NX) % 4, 4 - np.arange(NX) % 4)
    dj, di = np.meshgrid(d, d, indexing="ij")
    return np.minimum(dj, di), np.maximum(dj, di)


def hist_series(mem, names):
    """history の 0〜60 分の値を (time, ...) で組み立てる。LAND_WATER は最上層だけ。"""
    path = cm.hist_dir(mem)
    out = cm.read_hist(path, names, t=None)
    if "LAND_WATER" in out:
        out["LAND_WATER"] = out["LAND_WATER"][:, 0]
    return cm.hist_time(path), out


def compute():
    t, z = cm.read_restart(cm.restart_dir("anal", "mdet"), with_z=True)
    g = cm.read_restart(cm.restart_dir("gues", "mean"))
    a = cm.read_restart(cm.restart_dir("anal", "mean"))
    sg = cm.read_restart(cm.restart_dir("gues", "sprd"))
    T, G, A, SG = physical(t), physical(g), physical(a), physical_sprd(sg)
    wsg, _ = cm.wind_sprd()
    SG.update(wsg)
    keys = list(T)
    lo, hi = offset_class()
    res = {"keys": np.array(keys), "z": z,
           "rmse_g": [], "rmse_a": [], "sprd_g": [], "ratio_all": [], "ratio_dist": [], "ncol_dist": []}
    for k in keys:
        eg, ea = G[k] - T[k], A[k] - T[k]
        res["rmse_g"].append(rms(eg))
        res["rmse_a"].append(rms(ea))
        res["sprd_g"].append(rms(SG[k]))
        res["ratio_all"].append(rms(ea) / rms(eg))
        rd, nd = [], []
        for c in DCLS:
            m = (lo == c[0]) & (hi == c[1])
            rd.append(rms(ea[:, m]) / rms(eg[:, m]))
            nd.append(int(m.sum()))
        res["ratio_dist"].append(rd)
        res["ncol_dist"].append(nd)
    res["u_eg"] = (G["U [m/s]"] - T["U [m/s]"])[LEV]
    res["u_ea"] = (A["U [m/s]"] - T["U [m/s]"])[LEV]

    # 0〜60 分のばらつき（step 7 の history。20 member と mdet）
    names = ["U", "PREC", "LAND_WATER"]
    X = {v: [] for v in names}
    for m in range(20):
        tt, h = hist_series(f"{m + 1:04d}", names)
        for v in names:
            X[v].append(h[v])
    _, D = hist_series("mdet", names)
    res["time"] = tt
    for v in names:
        x = np.stack(X[v])                                   # (member, time, ...)
        ax = tuple(range(1, x.ndim - 1))
        res[f"sprd_{v}"] = np.sqrt(np.mean(x.var(0, ddof=1), axis=ax))
        res[f"err_{v}"] = np.sqrt(np.mean((x.mean(0) - D[v]) ** 2, axis=ax))
        res[f"mean_{v}"] = np.mean(D[v], axis=ax)
    np.savez(CACHE, **{k: np.asarray(v) for k, v in res.items()})
    return dict(np.load(CACHE))


def short(k):
    return k.split()[0]


def fig1(r):
    keys = list(r["keys"])
    fig, axs = plt.subplots(1, 2, figsize=(13, 4.6), gridspec_kw={"width_ratios": [1, 1.5]})

    # (a) 観測する U, V, T の誤差の大きさ
    ax = axs[0]
    obs = ["U [m/s]", "V [m/s]", "T [K]"]
    y = np.arange(len(obs))
    vals = [("観測誤差", [OBSERR] * 3, GRAY),
            ("予報の誤差（平均 − 真値）", [r["rmse_g"][keys.index(k)] for k in obs], C1),
            ("予報のばらつき", [r["sprd_g"][keys.index(k)] for k in obs], C3)]
    h = 0.26
    for n, (lab, v, c) in enumerate(vals):
        ax.barh(y + (n - 1) * h, v, height=h - 0.03, color=c, label=lab)
        for yy, vv in zip(y, v):
            ax.text(vv * 1.08, yy + (n - 1) * h, f"{vv:.3f}", va="center", fontsize=8, color="#52514e")
    ax.set_xscale("log")
    ax.set_xlim(1e-3, 0.4)
    ax.set_yticks(y, [short(k) for k in obs])
    ax.invert_yaxis()
    ax.set_xlabel("RMS（対数軸。U, V は m/s、T は K）")
    ax.set_title("(a) 60 分後の予報の誤差は、観測誤差の約 1/10", fontsize=11, loc="left")
    ax.legend(fontsize=8, loc="lower right", frameon=False)
    ax.grid(axis="x", alpha=0.3, which="both")

    # (b) 誤差 / ばらつき
    ax = axs[1]
    x = np.arange(len(keys))
    now = np.array(r["rmse_g"]) / np.array(r["sprd_g"])
    ax.bar(x - 0.2, [PREV[k] for k in keys], 0.38, color=GRAY, label="前回（1/1 開始・水蒸気の摂動）")
    ax.bar(x + 0.2, now, 0.38, color=C1, label="今回（1/31 開始・土壌水分の摂動）")
    for xx, v, pv in zip(x, now, [PREV[k] for k in keys]):
        ax.text(xx + 0.2, v - 0.03, f"{v:.2f}", ha="center", va="top", fontsize=8, color="white")
        ax.text(xx - 0.2, pv - 0.03, f"{pv:.2f}", ha="center", va="top", fontsize=8, color="white")
    ax.axhline(1, color="k", lw=1)
    ax.text(len(keys) - 0.5, 1.02, "理想 = 1", ha="right", va="bottom", fontsize=8)
    ax.set_xticks(x, [short(k) for k in keys])
    ax.set_ylim(0, 1.3)
    ax.set_ylabel("予報の誤差 ÷ 予報のばらつき")
    ax.set_title("(b) 真値がアンサンブルの中にいる（1 に近いほど良い）", fontsize=11, loc="left")
    ax.legend(fontsize=8, loc="upper left", frameon=False, ncol=2)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(f"{OUT}/fig1_ensemble.png", dpi=130)


def fig2(r):
    keys = list(r["keys"])
    rd = np.array(r["ratio_dist"])
    fig, axs = plt.subplots(1, 2, figsize=(14.5, 4.6), gridspec_kw={"width_ratios": [1.3, 1]})

    ax = axs[0]
    x = np.arange(len(keys))
    groups = [("全体", r["ratio_all"], C1), ("観測の柱", rd[:, 0], C2), ("観測の間（最も遠い柱）", rd[:, -1], C3)]
    for n, (lab, v, c) in enumerate(groups):
        ax.bar(x + (n - 1) * 0.27, np.asarray(v) - 1, 0.25, bottom=1, color=c, label=lab)
    ax.axhline(1, color="k", lw=1)
    ax.set_xticks(x, [short(k) for k in keys])
    ax.set_ylim(0.55, 1.3)
    ax.set_ylabel("解析の誤差 ÷ 予報の誤差")
    ax.text(-0.5, 0.57, "↓ 1 より小さい = 同化で真値に近づいた", fontsize=8, color="#52514e")
    ax.text(-0.5, 1.27, "↑ 1 より大きい = 同化で悪くなった", fontsize=8, color="#52514e", va="top")
    ax.set_title("(a) 観測のある柱では改善、観測の間では悪化が多い", fontsize=11, loc="left")
    ax.legend(fontsize=8, loc="upper left", frameon=False, bbox_to_anchor=(0.0, 0.93), ncol=3)
    ax.grid(axis="y", alpha=0.3)
    ax.text(len(keys) - 0.5, 0.57, "観測しているのは U, V, T だけ", fontsize=8, ha="right", color="#52514e")

    ax = axs[1]
    dkm = [2 * np.hypot(*c) for c in DCLS]
    for n, k in enumerate(keys):
        obsd = short(k) in ("U", "V", "T")
        ax.plot(dkm, rd[n], marker="o", ms=5, lw=2 if obsd else 1.2, ls="-" if obsd else "--",
                color=plt.cm.tab10(n), label=short(k) + ("（観測あり）" if obsd else ""))
    ax.axhline(1, color="k", lw=1)
    ax.set_xticks(dkm, [f"{d:.1f}" for d in dkm])
    ax.set_xlabel("最も近い観測の柱からの水平距離 [km]（観測は 8 km おき）")
    ax.set_ylabel("解析の誤差 ÷ 予報の誤差")
    ax.set_title("(b) 観測の柱から離れるほど改善が小さく、最も遠い柱では悪化", fontsize=11, loc="left")
    ax.legend(fontsize=8, frameon=False, loc="upper left", bbox_to_anchor=(1.01, 1))
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(f"{OUT}/fig2_effect.png", dpi=130)


def fig3(r):
    eg, ea = r["u_eg"], r["u_ea"]
    need, inc = -eg, ea - eg                       # 必要な修正（真値 − 予報）、LETKF の修正（解析 − 予報）
    jz, iz = ZOOM
    xs, ys = np.arange(NX)[iz] * 2 + 1, np.arange(NY)[jz] * 2 + 1
    vmax = 0.04
    fig = plt.figure(figsize=(17, 5.0), layout="constrained")
    gs = fig.add_gridspec(1, 4, width_ratios=[1, 1, 1, 1])
    jj, ii = np.nonzero(np.zeros((NY, NX), bool) | (np.add.outer(np.arange(NY) % 4, np.arange(NX) % 4) == 0))
    sel = (jj >= jz.start) & (jj < jz.stop) & (ii >= iz.start) & (ii < iz.stop)
    for n, (f, ttl) in enumerate([(need, "必要な修正（真値 − 予報）"), (inc, "LETKF の修正（解析 − 予報）"),
                                  (ea, "残った誤差（解析 − 真値）")]):
        ax = fig.add_subplot(gs[n])
        im = ax.pcolormesh(xs, ys, f[jz, iz], cmap="RdBu_r", vmin=-vmax, vmax=vmax, shading="nearest")
        ax.plot(ii[sel] * 2 + 1, jj[sel] * 2 + 1, "o", ms=3, mfc="none", mec="k", mew=0.7)
        ax.set_aspect("equal")
        ax.set_title(ttl, fontsize=10)
        ax.set_xlabel("x [km]")
        if n == 0:
            ax.set_ylabel("y [km]")
    cb = fig.colorbar(im, ax=fig.axes[:3], shrink=0.75, pad=0.01, aspect=30)
    cb.set_label("U [m/s]")

    ax = fig.add_subplot(gs[3])
    lo, hi = offset_class()
    for c, lab, col in [((2, 2), "観測の間（最も遠い柱）", C3), ((0, 0), "観測の柱", C2)]:
        m = (lo == c[0]) & (hi == c[1])
        xx, yy = need[m], inc[m]
        cc = np.corrcoef(xx, yy)[0, 1]
        ax.scatter(xx, yy, s=6, alpha=0.6, color=col, label=f"{lab}（相関 {cc:.2f}）", edgecolors="none")
    lim = 0.06
    ax.plot([-lim, lim], [-lim, lim], "k-", lw=0.8)
    ax.text(lim * 0.78, lim * 0.95, "理想（修正 = 必要な修正）", ha="right", va="top", fontsize=7.5, rotation=45, rotation_mode="anchor")
    ax.set_xlim(-lim, lim)
    ax.set_ylim(-lim, lim)
    ax.set_aspect("equal")
    ax.axhline(0, color="#cccccc", lw=0.6)
    ax.axvline(0, color="#cccccc", lw=0.6)
    ax.set_xlabel("必要な修正 [m/s]")
    ax.set_ylabel("LETKF の修正 [m/s]")
    ax.legend(fontsize=7.5, frameon=False, loc="lower right", markerscale=2.5, reverse=True)
    ax.set_title("修正量の比較（全領域の柱、この層）", fontsize=10)
    fig.suptitle(f"U、z = {r['z'][LEV]:.0f} m（層 {LEV + 1}）。左 3 枚は x 20〜120 km・y 20〜110 km を拡大、○ = 観測の柱（8 km おき）",
                 fontsize=11)
    fig.savefig(f"{OUT}/fig3_zoom.png", dpi=130)


def fig4(r):
    t = r["time"] / 60
    fig, axs = plt.subplots(1, 3, figsize=(14, 4.0))
    ax = axs[0]
    ax.plot(t, r["sprd_U"], "-o", color=C1, ms=4, label="ばらつき")
    ax.plot(t, r["err_U"], "-s", color=C2, ms=4, label="誤差（平均 − 真値）")
    ax.set_title("U（全格子点の RMS）", fontsize=10, loc="left")
    ax.set_ylabel("m/s")
    ax.text(0.02, 0.6, f"観測誤差 {OBSERR} m/s の\n約 1/10 までしか育っていない", transform=ax.transAxes, fontsize=8, color="#52514e")
    ax = axs[1]
    ax.plot(t, r["sprd_PREC"] * 3600, "-o", color=C1, ms=4, label="ばらつき")
    ax.plot(t, r["mean_PREC"] * 3600, "-^", color=GRAY, ms=4, label="真値の領域平均")
    ax.set_title("地上降水（mm/h）", fontsize=10, loc="left")
    ax.set_ylabel("mm/h")
    ax = axs[2]
    ax.plot(t, r["sprd_LAND_WATER"], "-o", color=C1, ms=4, label="ばらつき")
    ax.set_title("最上層（5 cm）の土壌水分", fontsize=10, loc="left")
    ax.set_ylabel("m³/m³")
    for ax in axs:
        ax.set_xlabel("初期時刻からの時間 [分]")
        ax.set_xticks(t)
        ax.set_ylim(bottom=0)
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8, frameon=False, loc="center left" if ax is axs[1] else "upper right" if ax is axs[2] else "upper left")
    fig.suptitle("1 cycle 目の予報（0〜60 分）: 摂動は土壌だけ → 大気のばらつきは育ち始めたところ", fontsize=11, x=0.01, ha="left")
    fig.tight_layout()
    fig.savefig(f"{OUT}/fig4_growth.png", dpi=130)


def main():
    r = dict(np.load(CACHE)) if os.path.exists(CACHE) else compute()
    os.makedirs(OUT, exist_ok=True)
    fig1(r)
    fig2(r)
    fig3(r)
    fig4(r)
    keys = list(r["keys"])
    print("観測の柱からの距離ごとの 解析/第一推定（距離 km: " + " ".join(f"{2 * np.hypot(*c):.1f}" for c in DCLS) + "）")
    for n, k in enumerate(keys):
        print(f"  {k:12s} " + " ".join(f"{v:.3f}" for v in r["ratio_dist"][n]))
    print("  柱の数: " + " ".join(str(v) for v in r["ncol_dist"][0]))
    print("0〜60 分: U のばらつき " + " ".join(f"{v:.4f}" for v in r["sprd_U"]))
    print("          U の誤差     " + " ".join(f"{v:.4f}" for v in r["err_U"]))
    print("          降水のばらつき [mm/h] " + " ".join(f"{v * 3600:.4f}" for v in r["sprd_PREC"]))
    print("          土壌水分のばらつき " + " ".join(f"{v:.4f}" for v in r["sprd_LAND_WATER"]))
    print(f"図: {OUT}/fig1_ensemble.png, fig2_effect.png, fig3_zoom.png, fig4_growth.png")


if __name__ == "__main__":
    main()
