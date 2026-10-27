#!/usr/bin/env python3
"""2026-10-07 のミーティング用の 1 枚: 制御なしの 6 cycle で、同化が効く大きさと、QC で捨てられる観測。

数値は run_soil_6cycle/check_cycles_fast.out・ジョブ 9844986 の標準出力・plot_6cycle_cache.npz（plot_6cycle.py）から読む。
使い方: cd analysis && STIME=20000131050000 python3 plot_summary.py
図は docs/phase7d/meeting_20261007/summary.png に出る。
"""
import numpy as np
import matplotlib.pyplot as plt

import common as cm
import plot_6cycle as p6                           # 日本語フォントの設定も読み込まれる

OUT = f"{cm.DOCS}/phase7d/meeting_20261007"

tab, qc = p6.read_table(), p6.read_qc()
r = dict(np.load(p6.CACHE))
u = tab["U [m/s]"]
cyc = np.arange(1, len(u) + 1)

fig, axs = plt.subplots(1, 2, figsize=(13, 5.2), gridspec_kw={"width_ratios": [1.5, 1]})

ax = axs[0]
ax.plot(cyc - 0.1, u[:, 0], "o-", color=p6.C1, ms=9, lw=2, label="同化の前（予報）")
ax.plot(cyc + 0.1, u[:, 1], "v", color=p6.C2, ms=10, label="同化の後（解析）")
for c, a, b in zip(cyc, u[:, 0], u[:, 1]):
    ax.plot([c - 0.1, c + 0.1], [a, b], color=p6.C2, lw=1.5)
    ax.text(c + 0.18, b, f"−{(1 - b / a) * 100:.0f}%", fontsize=10, va="center", color="#52514e")
ax.axhline(p6.OBSERR, color=p6.GRAY, ls="--", lw=1.5)
ax.text(0.7, p6.OBSERR + 0.012, "観測のノイズ 0.1", fontsize=10, color="#52514e")
ax.set_xticks(cyc)
ax.set_xlim(0.6, 6.7)
ax.set_ylim(0, 0.5)
ax.set_xlabel("何時間目の同化か", fontsize=11)
ax.set_ylabel("真値からのずれ（風 U）[m/s]", fontsize=11)
ax.text(0.98, 0.03, r"$\mathrm{RMSE}=\sqrt{\frac{1}{N}\sum_{i=1}^{N}(\bar{x}_i-x^*_i)^2}$" + "\n全格子点 N = 921,600、" + r"$\bar{x}$" + " = 20 member の平均、" + r"$x^*$" + " = 真値",
        transform=ax.transAxes, ha="right", va="bottom", fontsize=10, color="#52514e")
ax.set_title("ずれは育ち続け、同化で縮むのは数 %", fontsize=13, loc="left")
ax.legend(fontsize=10, frameon=False, loc="upper left")
ax.grid(alpha=0.3)

ax = axs[1]
uu = r["elm"] == 2819
omb, err = r["omb"][uu], r["err"][uu]
ok = np.isfinite(omb)
omb, err = omb[ok], err[ok]
rej = np.abs(omb) > p6.GROSS
vals = [np.sqrt(np.mean(err[~rej] ** 2)), np.sqrt(np.mean(err[rej] ** 2))]
labs = [f"使われた観測\n{(~rej).mean() * 100:.0f}%", f"QC で捨てられた観測\n{rej.mean() * 100:.0f}%"]
bars = ax.bar(labs, vals, color=[p6.C1, p6.C2], width=0.55)
for b, v in zip(bars, vals):
    ax.text(b.get_x() + b.get_width() / 2, v + 0.02, f"{v:.2f}", ha="center", fontsize=12)
ax.set_ylim(0, 1.1)
ax.set_ylabel("観測の位置での予報のずれ（RMS）[m/s]", fontsize=11)
ax.set_title("ずれの大きい場所の観測ほど捨てられる\n（6 時間目）", fontsize=13, loc="left")
ax.grid(axis="y", alpha=0.3)
ax.tick_params(axis="x", labelsize=11)

fig.tight_layout()
fig.savefig(f"{OUT}/summary.png", dpi=140)
print(f"図: {OUT}/summary.png")
print("同化での縮み [%]: " + " ".join(f"{(1 - b / a) * 100:.1f}" for a, b in u[:, :2]))
print(f"cycle 6: 使われた {vals[0]:.3f}、捨てられた {vals[1]:.3f}、捨てられた割合 {rej.mean() * 100:.1f}%")
