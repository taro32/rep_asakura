#!/usr/bin/env python3
"""Phase 7d「同化の精度の確認」(2)・(3): 感度実験の評価結果（check_cycles.py --fast・check_obspoint.py の .out）を並べて比べる。

読むもの: docs/phase7d/sens/<実験名>/check_cycles_fast.out・check_obspoint.out（sens/eval_job.sh の出力）
出力: 表（標準出力）と docs/phase7d/sens/compare_*.png
- 全格子点: 解析の RMSE（cycle 3〜6 の平均。long は 19〜24 時）、C' に対する比、同化での縮み、第一推定の 誤差 / ばらつき
- 観測の点（QC を通った観測）: 解析のずれ d_a と縮み、QC を通った観測の割合（cycle 6）

使い方: cd analysis && python3 compare_sens.py [組（既定 round1）]
  round1: 1 回目（HORI_LOCAL・INFL_MUL・RELAX_ALPHA）
  noda:   1 回目 ＋ 同化なし（NoDA）
  comb:   組み合わせ（member 数 × HORI_LOCAL）と同化なし
  long:   B-1 の 24 時間（TRUTH24・M80L10_24・NoDA24）。cycle 3〜6 の代わりに最後の 6 時間（19〜24 時）を平均する
  qcmem:  2 回目のうち基準の観測を使うもの（QC・member 数）。L10 も並べる
  cycle:  2 回目のうち自分で観測を作るもの（同化の間隔）。T60 が比べる相手
  all:    6 時間の感度実験すべてを、種類ごとの小さな図に分けて 1 枚に並べる（compare_all.png。縦軸は行ごとにそろえる）
比は各組の先頭の実験に対する比。
"""
import re
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import common as cm

SENS = f"{cm.DOCS}/phase7d/sens"
SETS = {
    "round1": ([("Cp", "C'（基準）", "k", "-"),
                ("L10", "L = 10 km", cm.C1, "-"), ("L50", "L = 50 km", cm.C1, "--"),
                ("I10", "INFL 1.0", cm.C2, "-"), ("I20", "INFL 2.0", cm.C2, "--"),
                ("R00", "RTPP 0.0", cm.C3, "-"), ("R05", "RTPP 0.5", cm.C3, "--")],
               "感度実験 1 回目: HORI_LOCAL（青）・INFL_MUL（橙）・RELAX_ALPHA（緑）。実線・破線 = 小さく・大きくした側"),
    "noda": ([("Cp", "C'（基準）", "k", "-"),
              ("L10", "L = 10 km", cm.C1, "-"), ("L50", "L = 50 km", cm.C1, "--"),
              ("I10", "INFL 1.0", cm.C2, "-"), ("I20", "INFL 2.0", cm.C2, "--"),
              ("R00", "RTPP 0.0", cm.C3, "-"), ("R05", "RTPP 0.5", cm.C3, "--"),
              ("NoDA", "同化なし", cm.GRAY, "-.")],
             "感度実験 1 回目 ＋ 同化なし（灰色の一点鎖線）: HORI_LOCAL（青）・INFL_MUL（橙）・RELAX_ALPHA（緑）"),
    "comb": ([("Cp", "C'（20 member・20 km）", "k", "-"),
              ("L10", "20 member・10 km", cm.C1, "-"), ("L5", "20 member・5 km", cm.C1, "--"),
              ("M40", "40 member・20 km", cm.C3, "-"), ("M40L10", "40 member・10 km", cm.C3, "--"),
              ("M80", "80 member・20 km", cm.C2, "-"), ("M80L10", "80 member・10 km", cm.C2, "--"),
              ("NoDA", "同化なし", cm.GRAY, "-.")],
             "組み合わせ: member 数（黒 20・緑 40・橙 80）× HORI_LOCAL（実線 20 km・破線 10 km。青は 20 member の 10・5 km）。灰色は同化なし"),
    "long": ([("TRUTH24", "20 member・20 km", "k", "-"),
              ("M80L10_24", "80 member・10 km", cm.C2, "-"),
              ("NoDA24", "同化なし", cm.GRAY, "-.")],
             "B-1: 24 時間（観測・真値は TRUTH24 のもの）"),
    "qcmem": ([("Cp", "C'（基準）", "k", "-"),
               ("Q10", "GROSS_ERROR 10", cm.C2, "-"), ("Q99", "GROSS_ERROR 99", cm.C2, "--"),
               ("M40", "40 member", cm.C3, "-"), ("L10", "L = 10 km（1 回目）", cm.C1, ":")],
              "感度実験 2 回目（基準の観測・真値）: QC（橙）・member 数（緑）"),
    "cycle": ([("T60", "60 分（比較用）", "k", "-"),
               ("T30", "30 分", cm.C1, "-"), ("T15", "15 分", cm.C1, "--")],
              "感度実験 2 回目（自分で作った観測・真値）: 同化の間隔"),
}
# all: 種類ごとの小さな図。どの図にも C'（黒）と同化なし（灰）を入れる。同化の間隔だけは観測・真値が別なので T60 が基準
GROUPS = [
    ("HORI_LOCAL（局所化の半径）", [("L5", "5 km", cm.C1, "--"), ("L10", "10 km", cm.C1, "-"), ("L50", "50 km", cm.C2, "-")]),
    ("INFL_MUL（inflation）", [("I10", "1.0", cm.C1, "-"), ("I20", "2.0", cm.C2, "-")]),
    ("RELAX_ALPHA（RTPP）", [("R00", "0.0（なし）", cm.C2, "-"), ("R05", "0.5", cm.C1, "-")]),
    ("GROSS_ERROR（QC）", [("Q10", "10", cm.C1, "-"), ("Q99", "99（QC なし）", cm.C1, "--")]),
    ("member 数・局所化の組み合わせ", [("M40", "40 member・20 km", cm.C3, "-"), ("M80", "80 member・20 km", cm.C2, "-"),
                                     ("M80L10", "80 member・10 km", cm.C2, "--")]),
    ("同化の間隔（観測・真値は別）", [("T30", "30 分", cm.C1, "-"), ("T15", "15 分", cm.C1, "--")]),
]
REFS = [("Cp", "C'（基準）", "k", "-"), ("NoDA", "同化なし", cm.GRAY, "-.")]
BASE = {"同化の間隔（観測・真値は別）": [("T60", "60 分（基準）", "k", "-")]}
SET = sys.argv[1] if len(sys.argv) > 1 else "round1"
EXPS, TITLE = SETS.get(SET, ([], ""))
SFX = "" if SET == "round1" else f"_{SET}"
KEYS = ["U [m/s]", "V [m/s]", "W [m/s]", "T [K]", "P [hPa]", "QV [g/kg]", "QHYD [g/kg]"]
LATE = slice(18, 24) if SET == "long" else slice(2, 6)   # 平均する時刻: cycle 3〜6（long は 19〜24 時）
LATE_LABEL = "19〜24 時" if SET == "long" else "cycle 3〜6"

cm.use_japanese_font()


def read_cycles(path):
    """check_cycles.py の出力 → {変数: (cycle, 8 列)}。列は RMSE 第一推定・解析・比・ばらつき 第一推定・解析・誤差/ばらつき・改善 観測の柱・観測の間。"""
    rows = {}
    for line in open(path):
        m = re.match(r"\s+(\S+ \[[^\]]+\])\s+(.*)", line)
        if m and "変数" not in line:
            rows.setdefault(m.group(1), []).append([float(x) for x in m.group(2).split()])
    return {k: np.array(v) for k, v in rows.items()}


def read_obspoint(path):
    """check_obspoint.py の出力 → {要素: (cycle, 列)}。列は 観測数, QC 通過数, QC 通過 d_b, d_a, 捨てた d_b, d_a, 全観測 d_b, d_a, 全格子点 b, a, ばらつき, 目安(ア), 目安(イ)。"""
    rows = {}
    for line in open(path):
        m = re.match(r"\s+([UVT])\s+(\d+)\s+(\d+)\s+\|(.*)", line)
        if not m:
            continue
        vals = [float(m.group(2)), float(m.group(3))]
        for part in m.group(4).split("|"):
            nums = part.replace("%", " ").split()
            vals += [float(x) for x in nums[:2]] if "%" in part else [float(x) for x in nums]   # 縮み [%] の列は除く
        rows.setdefault(m.group(1), []).append(vals)
    return {k: np.array(v) for k, v in rows.items()}


def plot_all():
    """6 時間の感度実験すべてを、種類ごとの列に分けて 1 枚に並べる。行: U・T の全格子点の RMSE、U のすべての観測の点の d_a。"""
    rows = [("U: 全格子点の解析の RMSE [m/s]", lambda c, o: c["U [m/s]"][:, 1]),
            ("T: 全格子点の解析の RMSE [K]", lambda c, o: c["T [K]"][:, 1]),
            ("U: すべての観測の点の d_a [m/s]", lambda c, o: o["U"][:, 7])]
    refs = {e for e, *_ in REFS}
    fig, axs = plt.subplots(len(rows), len(GROUPS), figsize=(4.0 * len(GROUPS), 3.3 * len(rows) + 0.8), sharex=True, sharey="row")
    for j, (gname, exps) in enumerate(GROUPS):
        lines = BASE.get(gname, REFS) + exps
        data = {e: (read_cycles(f"{SENS}/{e}/check_cycles_fast.out"), read_obspoint(f"{SENS}/{e}/check_obspoint.out")) for e, *_ in lines}
        for i, (rname, get) in enumerate(rows):
            ax = axs[i, j]
            for e, lab, col, ls in lines:
                y = get(*data[e])
                ax.plot(np.arange(1, len(y) + 1), y, ls, color=col, marker="o", ms=3, lw=1.8 if col == "k" else 1.3,
                        label=None if e in refs and j > 0 else lab)      # C'・同化なしの凡例は左端の列だけ
            ax.grid(alpha=0.3)
            if j == 0:
                ax.set_ylabel(rname, fontsize=9)
            if i == 0:
                ax.set_title(gname, fontsize=10, loc="left")
            if i == len(rows) - 1:
                ax.set_xlabel("解析時刻（開始からの時間）[h]")
        axs[0, j].legend(fontsize=7.5, frameon=False, loc="upper left")
    for i in range(len(rows)):
        axs[i, 0].set_ylim(bottom=0)                       # 全部描いてから下だけ 0 に（行で共通の縦軸なので上は全列の最大に合う）
    fig.suptitle("感度実験のまとめ（6 時間）。黒 = C'（基準: 20 member・HORI_LOCAL 20 km・INFL 1.45・RTPP 0.8・GROSS_ERROR 5・60 分）、"
                 "灰色の一点鎖線 = 同化なし。右端の列だけ観測・真値が別で、黒 = 60 分。縦軸は行ごとに共通", fontsize=11, x=0.01, ha="left")
    fig.tight_layout()
    fig.savefig(f"{SENS}/compare_all.png", dpi=110)
    print(f"図: {SENS}/compare_all.png")


def main():
    if SET == "all":
        plot_all()
        return
    C = {e: read_cycles(f"{SENS}/{e}/check_cycles_fast.out") for e, *_ in EXPS}
    O = {e: read_obspoint(f"{SENS}/{e}/check_obspoint.out") for e, *_ in EXPS}
    ref = C[EXPS[0][0]]

    print(f"全格子点の解析の RMSE（{LATE_LABEL} の平均）。かっこ内は {EXPS[0][1]} に対する比")
    print(f"{'実験':10s}" + "".join(f"{k.split()[0]:>16s}" for k in KEYS))
    for e, lab, *_ in EXPS:
        print(f"{lab:10s}" + "".join(f"{C[e][k][LATE, 1].mean():9.4f}({C[e][k][LATE, 1].mean() / ref[k][LATE, 1].mean():5.3f})"
                                     for k in KEYS))
    print(f"\n同化での縮み 1 − 解析/第一推定（全格子点、{LATE_LABEL} の平均）[%]")
    for e, lab, *_ in EXPS:
        print(f"{lab:10s}" + "".join(f"{(1 - C[e][k][LATE, 2].mean()) * 100:16.1f}" for k in KEYS))
    print(f"\n第一推定の 誤差 / ばらつき（全格子点、{LATE_LABEL} の平均。1 が理想。U, V, W は --fast では出ない）")
    for e, lab, *_ in EXPS:
        print(f"{lab:10s}" + "".join(f"{C[e][k][LATE, 5].mean():16.2f}" for k in KEYS[3:]))
    print("\n観測の点（最後の時刻）: QC を通った点の d_b → d_a（縮み）、全観測の d_a、ばらつき、目安(ア)、QC 通過率")
    for e, lab, *_ in EXPS:
        s = []
        for el in "UVT":
            r = O[e][el][-1]
            s.append(f"{el}: {r[2]:.3f}→{r[3]:.3f}（{(1 - r[3] / r[2]) * 100:4.1f}%）全 {r[7]:.3f} ばらつき {r[10]:.3f} 目安 {r[11]:.3f} QC {r[1] / r[0] * 100:4.1f}%")
        print(f"{lab:10s} " + "\n           ".join(s))

    plot(C, O)


def plot(C, O):
    cyc = np.arange(1, len(C[EXPS[0][0]]["U [m/s]"]) + 1)
    fig, axs = plt.subplots(2, 4, figsize=(20, 9))
    for ax, k in zip(axs.ravel()[:7], KEYS):
        for e, lab, col, ls in EXPS:
            ax.plot(cyc, C[e][k][:, 1], ls, color=col, marker="o", ms=3, lw=1.8 if e == EXPS[0][0] else 1.3, label=lab)
        ax.set_title(f"{k}: 全格子点の解析の RMSE", fontsize=10, loc="left")
        ax.set_xticks(cyc)
        ax.set_ylim(bottom=0)
        ax.grid(alpha=0.3)
    ax = axs.ravel()[7]
    for e, lab, col, ls in EXPS:
        ax.plot(cyc, O[e]["U"][:, 1] / O[e]["U"][:, 0] * 100, ls, color=col, marker="o", ms=3, label=lab)
    ax.set_title("U: QC を通った観測の割合 [%]", fontsize=10, loc="left")
    ax.set_xticks(cyc)
    ax.grid(alpha=0.3)
    axs[0, 0].legend(fontsize=8, frameon=False)
    for ax in axs[1]:
        ax.set_xlabel("cycle")
    fig.suptitle(TITLE, fontsize=12, x=0.01, ha="left")
    fig.tight_layout()
    fig.savefig(f"{SENS}/compare_grid{SFX}.png", dpi=120)

    fig, axs = plt.subplots(2, 3, figsize=(17, 9.2), sharex=True)
    units = {"U": "m/s", "V": "m/s", "T": "K"}
    for col, el in enumerate("UVT"):
        for row, (ic, ttl) in enumerate([(3, "QC を通った観測の点"), (7, "すべての観測の点（QC で捨てられた点も含む）")]):
            ax = axs[row, col]
            for e, lab, c, ls in EXPS:
                if row == 0 and e == "NoDA":
                    continue                       # 同化なしは QC で捨てる点がないので、上の段とは比べられない
                ax.plot(cyc, O[e][el][:, ic], ls, color=c, marker="o", ms=3, label=lab)
            if row == 0:
                ax.plot(cyc, O[EXPS[0][0]][el][:, 11], ":", color=cm.GRAY, label=f"目安 (ア)（{EXPS[0][1]}）")
            ax.axhline(cm.OBSERR, color="k", lw=0.8, ls="--")
            ax.set_title(f"{el}: {ttl}での解析のずれ d_a", fontsize=10, loc="left")
            ax.set_ylabel(f"RMS(H(解析の平均) − H(真値)) [{units[el]}]")
            ax.set_xticks(cyc)
            ax.set_ylim(bottom=0)
            ax.grid(alpha=0.3)
        axs[1, col].set_xlabel("cycle")
    axs[0, 0].legend(fontsize=8, frameon=False)
    axs[1, 0].legend(fontsize=8, frameon=False)
    fig.suptitle("観測の点での解析と真値の差（ノイズを除いた値）。上: QC を通った点だけ（QC で誤差の大きい点が外れるので小さく出る）、下: すべての点", fontsize=11, x=0.01, ha="left")
    fig.tight_layout()
    fig.savefig(f"{SENS}/compare_obspoint{SFX}.png", dpi=120)
    print(f"\n図: {SENS}/compare_grid{SFX}.png, compare_obspoint{SFX}.png")


if __name__ == "__main__":
    main()
