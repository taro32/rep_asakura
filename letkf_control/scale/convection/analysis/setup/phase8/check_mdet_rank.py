#!/usr/bin/env python3
"""Phase 8 の追加検証（2026-11-07）: 真値（mdet）が 80 member の中で何番目にいるかの時間変化（0〜24 時）。

result_m80（24 時間の cycle、80 member + mdet）の各 cycle の 1 時間予報の history から、目標領域
（x 70〜90 km・y 110〜130 km、格子 i 35〜44・j 55〜64、0 始まり）の平均を 10 分ごとにつないだもの
（`docs/control/20261102_soil_track/soil_track.npz`、analysis/control/20261102_soil_cov/plot_soil_track.py が作ったキャッシュ）を読む。
時刻 k × 600 s（k = 0〜144）。毎正時の値は前の cycle の 60 分の予報（解析の前）。

見る量:
  P10   降水強度（10 分ごとの瞬間値）[mm/h]
  Ympc  逐次の制御（docs/control/notes.md 1.3）の Y の近似: 時刻 t の窓 (t + 45, t + 75] 分の積算 [mm]。
        history は 10 分ごとの瞬間値なので、t + 50・60・70 分の 3 時刻 × 600 s の和で近似する（t = 0〜22 時）
  W020  土壌水分 0〜20 cm（第 1 層 0〜5 cm と第 2 層 5〜20 cm の厚さの重み平均）[m³/m³]
順位: 小さいほうから数える。同じ値（雨が 0 など）があるので、[mdet より小さい member の数 + 1, mdet 以下の member の数 + 1] の幅で表す。
  幅の下限が 81（全 member より大きい）・上限が 1（全 member より小さい）なら、分布の外。
土壌水分は、mdet とアンサンブル平均の差を、ばらつき（標準偏差）で割った値 z も出す（notes.md 1.4 の確認）。

使い方: cd analysis && python3 setup/phase8/check_mdet_rank.py
出力: 表（標準出力。docs/setup/phase8/mdet_rank/mdet_rank.out に保存する）と docs/setup/phase8/mdet_rank/mdet_rank.png
"""
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))   # analysis/common.py
import common as cm

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "../../../docs/control/20261102_soil_track/soil_track.npz")
OUT = os.path.join(HERE, "../../../docs/setup/phase8/mdet_rank")
NMEM = 80
DT = 600.0
DZ12 = np.array([0.05, 0.15])

cm.use_japanese_font()


def rank(ens, det):
    """ens（member, 時刻）、det（時刻）→ 順位の幅の下限・上限（小さいほうから、1〜81）。"""
    lo = (ens < det[None, :]).sum(axis=0) + 1
    hi = (ens <= det[None, :]).sum(axis=0) + 1
    return lo, hi


def main():
    z = np.load(CACHE)
    mems = [f"{k:04d}" for k in range(1, NMEM + 1)]
    P = np.array([z[f"{m}_tgt_PREC"] for m in mems]) * 3600.0                  # (member, 145) [mm/h]
    pd = z["mdet_tgt_PREC"] * 3600.0
    W = np.array([z[f"{m}_tgt_W"][:, :2] @ DZ12 / DZ12.sum() for m in mems])  # (member, 145)
    wd = z["mdet_tgt_W"][:, :2] @ DZ12 / DZ12.sum()
    nt = P.shape[1]
    th = np.arange(nt) * DT / 3600.0

    # 逐次の制御の Y の近似（t = 0〜22 時）
    hrs = np.arange(0, 23)
    idx = [hrs * 6 + o for o in (5, 6, 7)]                                    # t + 50・60・70 分
    Y = sum(P[:, i] for i in idx) / 3600.0 * DT                               # (member, 23) [mm]
    yd = sum(pd[i] for i in idx) / 3600.0 * DT

    rp = rank(P, pd)
    ry = rank(Y, yd)
    rw = rank(W, wd)
    zw = (wd - W.mean(axis=0)) / W.std(axis=0, ddof=1)

    os.makedirs(OUT, exist_ok=True)
    lines = []
    pr = lines.append
    pr("Phase 8 の追加検証: mdet の 80 member 中の順位（小さいほうから。幅 = 同じ値の member の分）")
    pr(f"データ: {os.path.relpath(CACHE, os.path.join(HERE, '../../..'))}")
    pr("")
    pr("== 逐次の制御の Y（窓 t+45〜75 分、10 分値 3 時刻で近似）")
    pr(" t [時]  mdet [mm]  member 平均  10%     50%     90%     最大    順位の幅   Y>0 の member 数")
    for k, t in enumerate(hrs):
        q = np.percentile(Y[:, k], [10, 50, 90])
        flag = "  外（最大より上）" if ry[0][k] == NMEM + 1 else ("  外（最小より下）" if ry[1][k] == 1 else "")
        pr(f" {t:5d}  {yd[k]:9.3f}  {Y[:, k].mean():10.3f}  {q[0]:6.3f}  {q[1]:6.3f}  {q[2]:6.3f}  {Y[:, k].max():6.3f}"
           f"  {ry[0][k]:3d}〜{ry[1][k]:3d}  {int((Y[:, k] > 0).sum()):5d}{flag}")
    pr("")
    pr("== 土壌水分 0〜20 cm（毎正時）")
    pr(" t [時]  mdet      member 平均  ばらつき   z = (mdet − 平均)/ばらつき  順位の幅")
    for k in range(0, nt, 6):
        pr(f" {th[k]:5.0f}  {wd[k]:.5f}  {W[:, k].mean():.5f}    {W[:, k].std(ddof=1):.5f}   {zw[k]:+8.2f}"
           f"                {rw[0][k]:3d}〜{rw[1][k]:3d}")
    pr("")
    out_p = (rp[0] == NMEM + 1) | (rp[1] == 1)
    rain = (P > 0).any(axis=0) | (pd > 0)
    pr(f"== 降水強度（10 分ごと）: 雨のある時刻 {int(rain.sum())} 個のうち、mdet が分布の外 {int((out_p & rain).sum())} 個"
       f"（最大より上 {int(((rp[0] == NMEM + 1) & rain).sum())}、最小より下 {int(((rp[1] == 1) & rain).sum())}）")
    text = "\n".join(lines)
    print(text)
    with open(f"{OUT}/mdet_rank.out", "w") as f:
        f.write(text + "\n")

    # 図
    fig, ax = plt.subplots(4, 1, figsize=(11, 13), sharex=True)
    a = ax[0]
    q = np.percentile(P, [10, 50, 90], axis=0)
    a.fill_between(th, q[0], q[2], color="0.8", label="member 10〜90%")
    a.plot(th, q[1], color="0.4", lw=1, label="member 中央値")
    a.plot(th, P.max(axis=0), color="0.6", lw=0.8, ls=":", label="member 最大")
    a.plot(th, pd, color="C3", lw=1.5, label="mdet")
    a.set_ylabel("降水強度 [mm/h]")
    a.set_title("目標領域の降水強度（10 分ごと）")
    a.legend(loc="upper left", fontsize=8)

    a = ax[1]
    tm = hrs + 1.0                                                              # 窓の中心（t + 60 分）に描く
    q = np.percentile(Y, [10, 50, 90], axis=0)
    a.fill_between(tm, q[0], q[2], color="0.8", label="member 10〜90%")
    a.plot(tm, q[1], color="0.4", lw=1, marker=".", label="member 中央値")
    a.plot(tm, Y.max(axis=0), color="0.6", lw=0.8, ls=":", label="member 最大")
    a.plot(tm, yd, color="C3", lw=1.5, marker="o", ms=3, label="mdet")
    a.set_ylabel("Y [mm]")
    a.set_title("逐次の制御の Y（介入の時刻 t の窓 t+45〜75 分。窓の中心 t+60 分に描く）")
    a.legend(loc="upper left", fontsize=8)

    a = ax[2]
    a.fill_between(th, rp[0], rp[1], color="C0", alpha=0.3, step="mid", label="降水強度（10 分ごと）")
    a.fill_between(tm, ry[0], ry[1], color="C3", alpha=0.4, step="mid", label="Y（窓 t+45〜75 分）")
    a.axhline(1, color="k", lw=0.5)
    a.axhline(NMEM + 1, color="k", lw=0.5)
    a.set_ylim(0, NMEM + 2)
    a.set_ylabel("mdet の順位（小さいほうから）")
    a.set_title("mdet の順位（幅 = 同じ値の member。1 = 全 member 以下、81 = 全 member より上）")
    a.legend(loc="upper left", fontsize=8)

    a = ax[3]
    a.plot(th, zw, color="C2", lw=1.5)
    a.axhline(0, color="k", lw=0.5)
    for v in (-2, 2):
        a.axhline(v, color="0.5", lw=0.5, ls="--")
    a.set_ylabel("z（土壌水分 0〜20 cm）")
    a.set_title("土壌水分 0〜20 cm: (mdet − member 平均) / member のばらつき")
    a.set_xlabel("時刻 [時]（1/31）")
    a.set_xlim(0, 24)
    a.set_xticks(range(0, 25, 2))
    for a in ax:
        a.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(f"{OUT}/mdet_rank.png", dpi=120)
    print(f"図: {OUT}/mdet_rank.png")


if __name__ == "__main__":
    main()
