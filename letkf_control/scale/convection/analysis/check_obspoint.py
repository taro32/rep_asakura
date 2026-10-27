#!/usr/bin/env python3
"""Phase 7d「同化の精度の確認」(1): 観測がある点だけで、解析・第一推定を真値（nature = mdet）と比べる。

観測は O = H(真値) + ε（ε の標準偏差 0.1）。O−A にはノイズ ε が混ざるので、ノイズを除いた次の量を観測ごとに出す:
  d_b = H(第一推定の平均) − H(真値)、 d_a = H(解析の平均) − H(真値)
- H は common.py の観測演算子（最も近い柱 + log p の線形内挿）。鉛直の内挿には、それぞれの状態の気圧を使う（LETKF と同じ）。
  - 真値: 前の時刻に始めた mdet の予報の 60 分の history（obsmake が観測を作ったもの）
  - 第一推定の平均: <t>/gues_letkf/mean（最後の時刻は <t>/gues/mean）、解析の平均: <t>/anal/mean の restart
- QC を通ったか: LETKF の obsdep（<OUTDIR>/obsdep/obsdep_<t>.dat）に入っている観測が、QC を通った観測。
  obsdep の O−B・O−A（LETKF 自身の値）と自前の値を比べ、観測演算子が合っていることを確かめる。
- 目安（観測 1 個だけで考えたときの解析の誤差）: σ_a² = σ_b² σ_o² / (σ_b² + σ_o²)、σ_o = 0.1。
  σ_b は (ア) LETKF が使うばらつき（obsdep の第一推定のばらつき × √INFL_MUL）と、(イ) 実際の誤差 RMSE(d_b) の 2 通り。
  周りの観測も使うので、実際はこれより小さくなりうる。これより大きければ、観測を十分に取り込めていない。
- 全格子点の RMSE（check_cycles.py と同じ定義）も並べる。

出力: 表（標準出力）と FIGDIR/obspoint_cycles.png・obspoint_levels.png
真値と観測は TRUTHDIR（既定 OUTDIR）から読む。同化の間隔が 1 時間でない実験は LCYCLE [s] を指定する（評価は 1 時間ごとの解析時刻）。感度実験は TRUTHDIR=…/result OUTDIR=…/sens/<実験名>。
使い方: STIME=20000131000000 FIGDIR=… python3 check_obspoint.py [解析時刻の数（既定: あるだけ）]
"""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import common as cm
from common import ELMS, OBSERR, physical, rms, tstr
from check_cycles import first

INFL_MUL = 1.45                                    # config.nml.letkf
BANDS = [(1100, 850), (850, 500), (500, 200), (200, 0)]   # 観測の気圧の帯 [hPa]
UNIT = {"U": "m/s", "V": "m/s", "T": "K"}

cm.use_japanese_font()


def match(obs, jj, ii, dep, djj, dii, tol=0.01):
    """obsdep の各観測が、観測ファイルの何番目かを返す。要素・格子点が同じで、気圧がいちばん近いもの
    （obsdep の気圧は Pa → hPa に直した値で、丸めの差がある。差が tol [hPa] を超えるものは -1）。"""
    cols = {}
    for n, key in enumerate(zip(obs[:, 0].astype(int), jj, ii)):
        cols.setdefault(key, []).append(n)
    cols = {k: np.array(v) for k, v in cols.items()}
    idx = np.full(len(dep), -1)
    for m, key in enumerate(zip(dep[:, 0].astype(int), djj, dii)):
        c = cols.get(key)
        if c is None:
            continue
        dp = np.abs(obs[c, 3] - dep[m, 3])
        if dp.min() <= tol:
            idx[m] = c[np.argmin(dp)]
    return idx


def H_state(F, pres, obs, jj, ii):
    """状態 F（{"U", "V", "T"}: (NZ, NY, NX)）の、観測ごとの値。pres [Pa]。"""
    h = np.full(len(obs), np.nan)
    for elm, name in ELMS.items():
        sel = np.flatnonzero(obs[:, 0] == elm)
        h[sel] = cm.obs_operator(F[name], pres, obs, jj, ii, sel)
    return h


def one_cycle(k):
    t = tstr(k)                                    # 1 時間ごとの解析時刻で評価する
    tprev = cm.tprev_of(t)                         # 第一推定の予報の開始（t − LCYCLE）
    d = f"{cm.OUTDIR}/{t}"
    obs = cm.read_obs(f"{cm.TRUTHDIR}/obs/obs_{t}.dat")
    dep = cm.read_obsdep(f"{cm.OUTDIR}/obsdep/obsdep_{t}.dat")

    # 真値: obsmake が観測を作った mdet の 60 分の history
    lon, lat, N = cm.read_global(cm.hist_dir("mdet", tprev, cm.TRUTHDIR))
    jj, ii, _ = cm.nearest_column(lon, lat, obs[:, 1], obs[:, 2])
    hn = H_state(N, N["PRES"], obs, jj, ii)

    # 第一推定・解析の平均（restart）と、全格子点の比較用の真値（check_cycles.py と同じ）
    pg = first(f"{d}/gues_letkf/mean", f"{d}/gues/mean")
    G = physical(cm.read_restart(pg, t))
    A = physical(cm.read_restart(f"{d}/anal/mean", t))
    dt = f"{cm.TRUTHDIR}/{t}"
    T = physical(cm.read_restart(first(f"{dt}/gues/mdet", f"{dt}/anal/mdet"), t))

    def as_obsvars(P):
        return {"U": P["U [m/s]"], "V": P["V [m/s]"], "T": P["T [K]"]}
    hg = H_state(as_obsvars(G), G["P [hPa]"] * 100.0, obs, jj, ii)
    ha = H_state(as_obsvars(A), A["P [hPa]"] * 100.0, obs, jj, ii)

    # obsdep との突き合わせ
    djj, dii, _ = cm.nearest_column(lon, lat, dep[:, 1], dep[:, 2])
    idx = match(obs, jj, ii, dep, djj, dii)
    if (idx < 0).any() or len(np.unique(idx)) != len(idx):
        sys.exit(f"{t}: obsdep と観測ファイルを突き合わせられません（見つからない {(idx < 0).sum()} 個、重複 {len(idx) - len(np.unique(idx))} 個）。")
    qc = np.zeros(len(obs), bool)
    qc[idx] = True
    sprd = np.full(len(obs), np.nan)
    sprd[idx] = dep[:, 11]
    omb_l = np.full(len(obs), np.nan)
    oma_l = np.full(len(obs), np.nan)
    omb_l[idx], oma_l[idx] = dep[:, 9], dep[:, 10]

    o = obs[:, 4]
    res = {"t": t, "elm": obs[:, 0], "lev": obs[:, 3], "qc": qc, "sprd": sprd,
           "eps": o - hn, "db": hg - hn, "da": ha - hn,
           "chk_b": (o - hg) - omb_l, "chk_a": (o - ha) - oma_l, "omb_l": omb_l, "path_g": os.path.relpath(pg, d),
           "grid": {}}
    for name, key in [("U", "U [m/s]"), ("V", "V [m/s]"), ("T", "T [K]")]:
        res["grid"][name] = (rms(G[key] - T[key]), rms(A[key] - T[key]))
    return res


def theory(sb):
    """観測 1 個で考えた解析の誤差 σ_a（σ_o = OBSERR）。"""
    return np.sqrt(sb ** 2 * OBSERR ** 2 / (sb ** 2 + OBSERR ** 2))


def summarize(r):
    """要素ごとの集計。"""
    out = {}
    for elm, name in ELMS.items():
        e = (r["elm"] == elm) & np.isfinite(r["db"]) & np.isfinite(r["da"])
        q = e & r["qc"]
        nq = e & ~r["qc"]
        sb = np.sqrt(INFL_MUL) * r["sprd"][q]
        out[name] = {
            "n": e.sum(), "nq": q.sum(),
            "eps": (r["eps"][e].mean(), r["eps"][e].std()),
            "all": (rms(r["db"][e]), rms(r["da"][e])),
            "qc": (rms(r["db"][q]), rms(r["da"][q])),
            "rej": (rms(r["db"][nq]), rms(r["da"][nq])) if nq.any() else (np.nan, np.nan),
            "sprd": rms(r["sprd"][q]),
            "th_sprd": rms(theory(sb)),
            "th_err": float(theory(rms(r["db"][q]))),
            "grid": r["grid"][name],
            "chk": (rms(r["chk_b"][q]), rms(r["chk_a"][q]), rms(r["omb_l"][q])),
            "bands": [],
        }
        for top, bot in BANDS:
            b = q & (r["lev"] <= top) & (r["lev"] > bot)
            out[name]["bands"].append((b.sum(), rms(r["db"][b]) if b.any() else np.nan, rms(r["da"][b]) if b.any() else np.nan))
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    ncyc = int(args[0]) if args else None
    rows = []
    k = 1
    while ncyc is None or k <= ncyc:
        t = tstr(k)
        if not os.path.isdir(f"{cm.OUTDIR}/{t}/anal/mean"):
            break
        r = one_cycle(k)
        s = summarize(r)
        rows.append((t, s))
        print(f"--- 解析時刻 {t}（cycle {k}）  第一推定: {r['path_g']}")
        print("   確認: ε = O − H(真値) の平均・標準偏差（0, 0.1 になるはず）、自前の O−B・O−A と LETKF（obsdep）の差の RMS")
        for name, v in s.items():
            print(f"     {name}: ε {v['eps'][0]:+.4f} {v['eps'][1]:.4f}   O−B の差 {v['chk'][0]:.2e}  O−A の差 {v['chk'][1]:.2e}"
                  f"（LETKF の O−B の RMS {v['chk'][2]:.4f}）")
        print(f"   {'要素':4s} {'観測数':>6s} {'QC通過':>6s} | {'QC 通過 d_b':>11s} {'d_a':>7s} {'縮み':>6s} | {'捨てた d_b':>10s} {'d_a':>7s} {'縮み':>6s}"
              f" | {'全観測 d_b':>10s} {'d_a':>7s} {'縮み':>6s} | {'全格子点 b':>10s} {'a':>7s} {'縮み':>6s}"
              f" | {'ばらつき':>8s} {'目安(ア)':>8s} {'目安(イ)':>8s}")
        for name, v in s.items():
            def f(p):
                return f"{p[0]:10.4f} {p[1]:7.4f} {(1 - p[1] / p[0]) * 100:5.1f}%"
            print(f"   {name:4s} {v['n']:6d} {v['nq']:6d} | {f(v['qc'])} | {f(v['rej'])} | {f(v['all'])} | {f(v['grid'])}"
                  f" | {v['sprd']:8.4f} {v['th_sprd']:8.4f} {v['th_err']:8.4f}")
        print("   気圧の帯ごと（QC を通った観測）: 帯 [hPa]  個数  d_b → d_a（縮み）")
        for name, v in s.items():
            print(f"     {name}: " + "  ".join(f"{top}–{bot}: {n} {b:.3f}→{a:.3f}（{(1 - a / b) * 100:.0f}%）"
                                           for (top, bot), (n, b, a) in zip(BANDS, v["bands"]) if n))
        sys.stdout.flush()
        k += 1
    if not rows:
        sys.exit("解析時刻が見つかりません。")
    out = cm.figdir()
    plot_cycles(rows, out)
    plot_levels(rows, out)
    print(f"\n図: {out}/obspoint_cycles.png, obspoint_levels.png")


def saw(ax, cyc, pairs, **kw):
    """第一推定 → 解析 ののこぎり型の線。"""
    x, y = [], []
    for c, (b, a) in zip(cyc, pairs):
        x += [c - 0.15, c + 0.15]
        y += [b, a]
    return ax.plot(x, y, **kw)


def plot_cycles(rows, out):
    cyc = np.arange(1, len(rows) + 1)
    fig, axs = plt.subplots(1, 3, figsize=(17, 5.0))
    for ax, name in zip(axs, ELMS.values()):
        S = [s[name] for _, s in rows]
        saw(ax, cyc, [v["qc"] for v in S], color=cm.C1, marker="o", ms=4, label="観測の点（QC を通った観測）")
        saw(ax, cyc, [v["all"] for v in S], color=cm.C2, marker="s", ms=4, label="観測の点（すべて）")
        saw(ax, cyc, [v["grid"] for v in S], color=cm.GRAY, marker="^", ms=4, label="全格子点")
        ax.plot(cyc + 0.15, [v["th_sprd"] for v in S], ":", color=cm.C3, marker="x", label="目安 (ア): ばらつきから")
        ax.plot(cyc + 0.15, [v["th_err"] for v in S], "--", color=cm.C3, marker="+", label="目安 (イ): 実際の誤差から")
        ax.axhline(OBSERR, color="k", lw=0.8, ls="--")
        ax.text(cyc[-1] + 0.4, OBSERR, "観測誤差", fontsize=8, va="bottom", ha="right")
        ax.set_title(f"{name}: 真値からのずれ（RMS）", fontsize=11, loc="left")
        ax.set_xlabel("cycle（各 cycle の左 = 同化の前、右 = 同化の後）")
        ax.set_ylabel(f"[{UNIT[name]}]")
        ax.set_xticks(cyc)
        ax.set_ylim(bottom=0)
        ax.grid(alpha=0.3)
    axs[0].legend(fontsize=8, frameon=False, loc="upper left")
    fig.suptitle("観測がある点での、第一推定・解析と真値の差（ノイズを除いた値）", fontsize=12, x=0.01, ha="left")
    fig.tight_layout()
    fig.savefig(f"{out}/obspoint_cycles.png", dpi=130)


def plot_levels(rows, out):
    cyc = np.arange(1, len(rows) + 1)
    fig, axs = plt.subplots(1, 3, figsize=(17, 4.6), sharey=True)
    for ax, name in zip(axs, ELMS.values()):
        for nb, ((top, bot), col) in enumerate(zip(BANDS, [cm.C1, cm.C2, cm.C3, cm.GRAY])):
            v = [s[name]["bands"][nb] for _, s in rows]
            if not any(n for n, _, _ in v):
                continue
            ax.plot(cyc, [(1 - a / b) * 100 for _, b, a in v], "-o", color=col, ms=4, label=f"{top}–{bot} hPa")
        ax.axhline(0, color="k", lw=0.8)
        ax.set_title(f"{name}: 同化で縮んだ割合（QC を通った観測の点）", fontsize=11, loc="left")
        ax.set_xlabel("cycle")
        ax.set_xticks(cyc)
        ax.grid(alpha=0.3)
    axs[0].set_ylabel("1 − RMS(d_a) / RMS(d_b) [%]")
    axs[0].legend(fontsize=8, frameon=False)
    fig.tight_layout()
    fig.savefig(f"{out}/obspoint_levels.png", dpi=130)


if __name__ == "__main__":
    main()
