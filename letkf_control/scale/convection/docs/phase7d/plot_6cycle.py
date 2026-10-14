#!/usr/bin/env python3
"""Phase 7d の 6 cycle（ジョブ 9844986、制御なし）の結果を、ミーティング用の図にまとめる。

- fig5_cycles.png: cycle ごとの U の誤差（第一推定 → 解析）、誤差 / ばらつき、解析 / 第一推定、QC を通った観測の割合
  （run_soil_6cycle/check_cycles_fast.out と、ジョブの標準出力の OBSERVATION COUNTS から読む）
- fig6_qc.png:     cycle 6 の QC: |O−B| の分布と 0.5 のしきい値、捨てられた観測の場所と真値の雲・降水

fig6 の O−B は check_obsmake.py と同じ内挿で、20 member の 60 分の history から H を計算して平均する。
計算結果は OUTDIR/plot_6cycle_cache.npz に保存する（作り直すときは消す）。

使い方:
  cd docs/phase7d && STIME=20000131050000 python3 plot_6cycle.py
  （STIME は cycle 6 の第一推定を作った時刻。観測は STIME + 1h）
"""
import os
import re
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, f"{HERE}/../phase7")
import check_obsmake as co                         # noqa: E402

from plot_1cycle import C1, C2, C3, GRAY           # noqa: E402,F401（日本語フォントの設定も読み込まれる）

OUT = f"{HERE}/run_soil_6cycle"
TABLE = f"{OUT}/check_cycles_fast.out"
JOBOUT = "/work/02/gv42/v42013/scale-letkc/letkf_control/scale/tmp/convection/cycle_job.sh.9844986.out"
CACHE = f"{co.OUTDIR}/plot_6cycle_cache.npz"
OBSERR, GROSS = 0.1, 0.5
NOBS = 28448                                       # 要素ごとの観測の数（QC の前）


def read_table():
    """check_cycles.py の出力から {変数: (cycle, 6 列)} を読む。列は RMSE 第一推定, 解析, 比, ばらつき 第一推定, 解析, 誤差/ばらつき。"""
    rows = {}
    for line in open(TABLE):
        m = re.match(r"\s+(\S+ \[[^\]]+\])\s+(.*)", line)
        if m and "変数" not in line:
            vals = [float(x) for x in m.group(2).split()]
            rows.setdefault(m.group(1), []).append(vals)
    return {k: np.array(v) for k, v in rows.items()}


def read_qc():
    """ジョブの標準出力から、cycle ごとの QC 後の観測の数（U, V, T）を読む（LETKF の分だけ。LETKC は TOTAL 1 個）。"""
    out = []
    lines = open(JOBOUT).read().splitlines()
    for n, line in enumerate(lines):
        if line.startswith("OBSERVATION COUNTS (GLOABL"):
            c = {}
            for l2 in lines[n + 1:n + 10]:
                m = re.match(r"ADPUPA\s+(U|V|T)\s+(\d+)\s+(\d+)", l2)
                if m:
                    c[m.group(1)] = int(m.group(3))
            if c:
                out.append([c["U"], c["V"], c["T"]])
    return np.array(out)


def compute():
    """cycle 6 の観測ごとの O−B・H(平均) − H(真値) と、真値の雲・降水の柱の最大値。"""
    from netCDF4 import Dataset
    import glob
    co.HIST = f"{co.OUTDIR}/{co.T0}/hist/mdet"
    lon, lat, D = co.read_global()
    obs = co.read_obs(co.OBS)
    jj, ii, _ = co.nearest_column(lon, lat, obs[:, 1], obs[:, 2])

    def H(var):
        h = np.full(len(obs), np.nan)
        for elm, name in co.ELMS.items():
            for n in np.flatnonzero(obs[:, 0] == elm):
                h[n] = co.interp_logp(var[name][:, jj[n], ii[n]], var["PRES"][:, jj[n], ii[n]], obs[n, 3] * 100.0)
        return h

    ht = H(D)
    hs = []
    for m in range(1, 21):
        co.HIST = f"{co.OUTDIR}/{co.T0}/hist/{m:04d}"
        hs.append(H(co.read_global()[2]))
    hm = np.mean(hs, axis=0)
    qh = np.full((co.NY, co.NX), np.nan)
    for f in sorted(glob.glob(f"{co.OUTDIR}/{co.T0}/hist/mdet/history.pe*.nc")):
        with Dataset(f) as d:
            it = int(np.flatnonzero(np.isclose(d.variables["time"][:], co.T_OBS))[0])
            i = np.rint(d.variables["x"][:] / co.DX - 0.5).astype(int)
            j = np.rint(d.variables["y"][:] / co.DX - 0.5).astype(int)
            qh[np.ix_(j, i)] = np.asarray(d.variables["QHYD"][it]).max(axis=0) * 1e3
    np.savez(CACHE, elm=obs[:, 0], omb=obs[:, 4] - hm, err=hm - ht, jj=jj, ii=ii, qh=qh)
    return dict(np.load(CACHE))


def fig5(tab, qc):
    cyc = np.arange(1, len(tab["U [m/s]"]) + 1)
    fig, axs = plt.subplots(1, 4, figsize=(19, 4.6))

    ax = axs[0]
    x, y = [], []
    for c, r in zip(cyc, tab["U [m/s]"]):
        x += [c - 0.12, c + 0.12]
        y += [r[0], r[1]]
    ax.plot(x, y, "-", color=C1, lw=1.5)
    ax.plot(cyc - 0.12, tab["U [m/s]"][:, 0], "o", color=C1, ms=6, label="予報（第一推定）")
    ax.plot(cyc + 0.12, tab["U [m/s]"][:, 1], "v", color=C2, ms=6, label="解析")
    ax.axhline(OBSERR, color=GRAY, ls="--", lw=1.2)
    ax.text(6.3, OBSERR + 0.01, "観測誤差 0.1", ha="right", fontsize=8, color="#52514e")
    ax.set_ylabel("U の誤差（全格子点の RMS）[m/s]")
    ax.set_title("(a) 誤差は育ち続け、同化で少ししか減らない", fontsize=10.5, loc="left")
    ax.legend(fontsize=8, frameon=False, loc="upper left")

    ax = axs[1]
    for k, c in [("T [K]", C1), ("P [hPa]", C3), ("QV [g/kg]", C2), ("QHYD [g/kg]", "#4a3aa7")]:
        ax.plot(cyc, tab[k][:, 5], "-o", color=c, ms=5, label=k.split()[0])
    ax.axhline(1, color="k", lw=1)
    ax.set_ylim(0.6, 1.5)
    ax.set_ylabel("予報の誤差 ÷ 予報のばらつき")
    ax.set_title("(b) ばらつきは誤差と一緒に育つ（1 = 理想）", fontsize=10.5, loc="left")
    ax.legend(fontsize=8, frameon=False, ncol=2, loc="upper left")

    ax = axs[2]
    for k, c, ls in [("U [m/s]", C1, "-"), ("V [m/s]", "#e87ba4", "-"), ("T [K]", C2, "-"),
                     ("P [hPa]", C3, "--"), ("QV [g/kg]", "#eda100", "--"), ("QHYD [g/kg]", "#4a3aa7", "--")]:
        ax.plot(cyc, tab[k][:, 2], ls, marker="o", color=c, ms=5, label=k.split()[0])
    ax.axhline(1, color="k", lw=1)
    ax.set_ylim(0.7, 1.05)
    ax.set_yticks(np.arange(0.7, 1.051, 0.05))
    ax.set_ylabel("解析の誤差 ÷ 予報の誤差")
    ax.text(0.02, 0.03, "↓ 小さいほど同化が効いた（実線 = 観測している変数）", transform=ax.transAxes, fontsize=8, color="#52514e")
    ax.set_title("(c) 同化の効果は cycle 2 が最大、その後は 1〜5%", fontsize=10.5, loc="left")
    ax.legend(fontsize=8, frameon=False, ncol=3, loc="lower right", bbox_to_anchor=(1, 0.07))

    ax = axs[3]
    for n, (lab, c) in enumerate([("U", C1), ("V", "#e87ba4"), ("T", C2)]):
        ax.plot(cyc, qc[:len(cyc), n] / NOBS * 100, "-o", color=c, ms=5, label=lab)
    ax.set_ylim(80, 101)
    ax.set_ylabel("QC を通った観測 [%]")
    ax.set_title("(d) 誤差が育つと、QC で捨てられる観測が増える", fontsize=10.5, loc="left")
    ax.text(0.02, 0.03, f"|観測 − 予報| > {GROSS}（観測誤差 × 5）を捨てる", transform=ax.transAxes, fontsize=8, color="#52514e")
    ax.legend(fontsize=8, frameon=False, loc="upper right")

    for ax in axs:
        ax.set_xticks(cyc)
        ax.set_xlabel("cycle（解析時刻 = 開始から何時間後か）")
        ax.grid(alpha=0.3)
    axs[0].set_ylim(bottom=0)
    fig.suptitle("制御なしの 6 cycle（1/31 00 時開始、土壌水分の摂動、ジョブ 9844986）", fontsize=12, x=0.01, ha="left")
    fig.tight_layout()
    fig.savefig(f"{OUT}/fig5_cycles.png", dpi=130)


def fig6(r):
    u = r["elm"] == 2819
    omb, err = r["omb"][u], r["err"][u]
    ok = np.isfinite(omb)
    omb, err, jj, ii = omb[ok], err[ok], r["jj"][u][ok], r["ii"][u][ok]
    rej = np.abs(omb) > GROSS
    fig = plt.figure(figsize=(17, 5.0), layout="constrained")
    gs = fig.add_gridspec(1, 3, width_ratios=[1, 0.75, 1.1])

    ax = fig.add_subplot(gs[0])
    bins = np.linspace(-3, 3, 121)
    ax.hist(omb[~rej], bins=bins, color=C1, label=f"使われた {(~rej).sum()} 個（{(~rej).mean() * 100:.0f}%）")
    ax.hist(omb[rej], bins=bins, color=C2, label=f"捨てられた {rej.sum()} 個（{rej.mean() * 100:.0f}%）")
    for s in (-GROSS, GROSS):
        ax.axvline(s, color="k", lw=1, ls="--")
    ax.set_yscale("log")
    ax.set_xlabel("観測 − 予報（O−B）[m/s]")
    ax.set_ylabel("観測の数（対数軸）")
    ax.set_title("(a) U の O−B の分布。±0.5 の外は QC で捨てられる", fontsize=10.5, loc="left")
    ax.legend(fontsize=8, frameon=False, loc="upper left")
    ax.grid(alpha=0.3)

    ax = fig.add_subplot(gs[1])
    vals = [np.sqrt(np.mean(err[~rej] ** 2)), np.sqrt(np.mean(err[rej] ** 2)), np.sqrt(np.mean(err ** 2))]
    labs = ["使われた観測\nの場所", "捨てられた観測\nの場所", "全観測\n（参考）"]
    bars = ax.bar(labs, vals, color=[C1, C2, GRAY], width=0.6)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.02, f"{v:.2f}", ha="center", fontsize=9)
    ax.axhline(OBSERR, color=GRAY, ls="--", lw=1)
    ax.text(2.3, OBSERR + 0.02, "観測誤差 0.1", ha="right", fontsize=8, color="#52514e")
    ax.set_ylabel("予報の誤差 RMS（H(平均) − H(真値)）[m/s]")
    ax.set_title("(b) 誤差の大きい点ほど観測が使われない", fontsize=10.5, loc="left")
    ax.grid(axis="y", alpha=0.3)

    ax = fig.add_subplot(gs[2])
    x = np.arange(co.NX) * 2 + 1
    im = ax.pcolormesh(x, x, r["qh"], cmap="Blues", vmin=0, vmax=np.nanpercentile(r["qh"], 99), shading="nearest")
    fig.colorbar(im, ax=ax, shrink=0.85, label="真値の雲・降水（柱の最大）[g/kg]")
    nrej = np.zeros((co.NY, co.NX), int)
    np.add.at(nrej, (jj[rej], ii[rej]), 1)
    j0, i0 = np.nonzero(nrej)
    sc = ax.scatter(i0 * 2 + 1, j0 * 2 + 1, s=4 + 4 * nrej[j0, i0], facecolors="none", edgecolors=C2, linewidths=1.0)
    ax.set_aspect("equal")
    ax.set_xlabel("x [km]")
    ax.set_ylabel("y [km]")
    ax.set_title("(c) 捨てられた U の観測の柱（○ が大きいほど多くの層）。\n対流の中に限らず、領域全体に散らばる", fontsize=10.5, loc="left")
    fig.suptitle("cycle 6（解析時刻 06 時）の QC。GROSS_ERROR = 5 × 観測誤差 0.1 = 0.5 m/s", fontsize=12)
    fig.savefig(f"{OUT}/fig6_qc.png", dpi=130)
    print(f"cycle 6 の U: 捨てられた {rej.sum()} / {len(rej)}、予報誤差 使われた {vals[0]:.3f} 捨てられた {vals[1]:.3f} 全部 {vals[2]:.3f}")
    print(f"  捨てられた観測のある柱 {len(j0)} 本のうち、真値の雲・降水（> 0.01 g/kg）がある柱 {(r['qh'][j0, i0] > 0.01).mean() * 100:.0f}%"
          f"（全領域では {(r['qh'] > 0.01).mean() * 100:.0f}%）")


def main():
    tab, qc = read_table(), read_qc()
    r = dict(np.load(CACHE)) if os.path.exists(CACHE) else compute()
    fig5(tab, qc)
    fig6(r)
    print(f"図: {OUT}/fig5_cycles.png, fig6_qc.png")


if __name__ == "__main__":
    main()
