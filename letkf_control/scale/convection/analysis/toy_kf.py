#!/usr/bin/env python3
"""データ同化の誤差の時間変化を、いちばん簡単なモデルで確かめる（docs/phase7d/theory_da_error.md の付録）。

1. スカラーのカルマンフィルタ: 予報で誤差の分散が a² 倍、解析で P_a = P_f R / (P_f + R)。
   定常状態 P_f* = (a² − 1) R に収束することを、数値で確かめる。
2. 見えない成分がある場合: 誤差を「観測で見える成分」と「見えない成分」に分ける。見えない成分は解析で減らず、
   予報の非線形性で飽和の大きさまで育つ（飽和に近づくほど伸びが鈍る形で近似）。全体の誤差の時間変化を、同化あり・なしで描く。

使い方: python3 toy_kf.py [a（1 cycle の成長率、既定 2.0）] [観測誤差 σ_o（既定 0.1）] [見える成分の割合（既定 0.4）]
出力: 表（標準出力）と toy_kf.png（カレントディレクトリ）
"""
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import common as cm

cm.use_japanese_font()

a = float(sys.argv[1]) if len(sys.argv) > 1 else 2.0
so = float(sys.argv[2]) if len(sys.argv) > 2 else 0.1
frac = float(sys.argv[3]) if len(sys.argv) > 3 else 0.4
R = so ** 2
N = 24
SAT = 0.6                                         # 飽和の大きさ（標準偏差）


def grow(P, Psat):
    """予報 1 cycle: 小さいうちは分散を a² 倍にし、飽和の分散 Psat に近づくほど伸びが鈍る（行き過ぎない形。P が小さいと a² P）。"""
    return Psat * a ** 2 * P / (Psat + (a ** 2 - 1) * P)


def run(da, P0=1e-4):
    Pv, Pu = frac * P0, (1 - frac) * P0           # 見える成分・見えない成分の分散
    out = []
    for _ in range(N):
        Pv, Pu = grow(Pv, frac * SAT ** 2), grow(Pu, (1 - frac) * SAT ** 2)   # 全体の飽和が SAT² になるように分ける
        f = np.sqrt(Pv + Pu)
        if da:
            Pv = Pv * R / (Pv + R)                # 見える成分だけ解析で減る
        out.append((f, np.sqrt(Pv + Pu)))
    return np.array(out)


# 1. 純粋なスカラーのカルマンフィルタ（飽和なし、すべて見える）
print(f"1. スカラーのカルマンフィルタ（a = {a}、σ_o = {so}）: 予報 → 解析の標準偏差")
Pf = 1e-4
for k in range(1, 11):
    Pa = Pf * R / (Pf + R)
    print(f"   cycle {k:2d}: {np.sqrt(Pf):.3f} → {np.sqrt(Pa):.3f}")
    Pf = a ** 2 * Pa
print(f"   定常状態: 予報 √((a²−1)R) = {np.sqrt((a ** 2 - 1) * R):.3f}、解析 √((a²−1)R/a²) = {np.sqrt((a ** 2 - 1) * R / a ** 2):.3f}")

# 2. 見えない成分と飽和がある場合
da, no = run(True), run(False)
print(f"\n2. 見える成分 {frac * 100:.0f}%・飽和 {SAT}: 解析の標準偏差（同化あり / 同化なし）")
for k in [1, 2, 3, 6, 12, 24]:
    print(f"   cycle {k:2d}: {da[k - 1, 1]:.3f} / {no[k - 1, 1]:.3f}")
cyc = np.arange(1, N + 1)
fig, ax = plt.subplots(figsize=(7, 4.2))
x = np.repeat(cyc, 2) + np.tile([-0.15, 0.15], N)
ax.plot(x, da.ravel(), "-", color="#2a78d6", label="同化あり（予報 → 解析）")
ax.plot(cyc, no[:, 1], "-.", color="#8c8b86", label="同化なし")
ax.axhline(SAT, color="k", lw=0.8, ls=":")
ax.text(N, SAT, "飽和", ha="right", va="bottom", fontsize=8)
ax.axhline(so, color="k", lw=0.8, ls="--")
ax.text(N, so, "観測誤差", ha="right", va="bottom", fontsize=8)
ax.set_xlabel("cycle")
ax.set_ylabel("誤差の標準偏差")
ax.set_title(f"a = {a}、見える成分 {frac * 100:.0f}%", fontsize=10, loc="left")
ax.legend(frameon=False, fontsize=9)
ax.set_ylim(bottom=0)
ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig("toy_kf.png", dpi=110)
print("\n図: toy_kf.png")
