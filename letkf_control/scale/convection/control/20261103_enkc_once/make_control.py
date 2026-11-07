#!/usr/bin/env python3
"""EnKC の修正量を計算し、mdet（真値）に足した制御実験の入力を作る（2026-11-03）。

アンサンブル: phase9_patch_t08（8 時にパッチ型の土壌水分の摂動を入れ、18 時まで予報した 80 member）。
目標 Y: 目標領域（20 km 四方、1 パッチ）の雨。2 通り（TARGETS）。σ_R = σ_Y。
状態（制御する量）: 第 1・2 層（0〜20 cm）の土壌水分。member の違いはパッチの摂動（perturbation.npz）で表す
  （8 時の解析そのもののばらつき 約 0.001 は無視する）。両層に同じ修正量を足す
状態の表し方 A（2 通り）:
  full  場全体: 格子ごとに Δθ = cov(θ, Y) / (σ_Y² + σ_R²) · (y* − Ȳ)
  local 目標のパッチと周りの 8 パッチの 2 自由度に絞る: z = (目標のパッチの平均, 周りの 8 パッチの平均) に同じ式を使い、
        目標のパッチ・周りの 8 パッチにそれぞれ一様に足す（それより外は 0）
湿らせる向きだけ（clip）: 修正量の負の部分を 0 にする。比べるため、切らない場合（noclip）も流す
比べるもの: 修正なし（mdet をそのまま流し直す）、ランダムな場所（local・clip の修正量を、ランダムに選んだ 3×3 パッチへずらす）

予測（線形）: 目標のパッチと周りの 8 パッチの平均への、Y の重回帰 Y ≈ a + b_T z_T + b_S z_S から ΔY = b_T Δz_T + b_S Δz_S
  （full の、それより外の修正は予測に入れない）

作るもの（OUT = /work/gv42/v42013/20260923_enkc_convection/<NAME>）:
  OUT/init/<n>/…、OUT/work/<n>/run.d01_<T_INT>.conf、OUT/work/launcher.conf、OUT/control.npz（修正量・予測・設定）
使い方: [DRY=1] python3 make_control.py（DRY=1 は修正量の表だけ出す）
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "../20261103_patch_fcst"))
import make_patch_fcst as mp

NAME = os.environ.get("NAME", "phase9_control_t08")
OUT = f"{mp.BASE}/{NAME}"
ENS = f"{mp.BASE}/phase9_patch_t08"
HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = f"{HERE}/../../docs/control/20261103_patch_fcst/patch_fcst.npz"   # check_patch_fcst.py の目標領域の時系列
T0 = 8
I0, J0, K = 35, 55, 10                                           # 目標領域（= 1 パッチ）
NMEM = 80
SEED = 20261104
# 目標: 名前 → (時間帯 [時], y* [mm])
TARGETS = {"p1314": ((13, 14), 0.0),      # 13〜14 時の雨をなくす（降り始めを 14 時より後へ）
           "p1317": ((13, 17), 8.0)}      # 13〜17 時の合計を 8 mm に


def target_y():
    """member（80）と mdet の、目標ごとの Y [mm]。"""
    c = np.load(CACHE)
    hr = lambda p: p[..., 1:].reshape(*p.shape[:-1], -1, 6).mean(axis=-1)   # 列 h = T0 + h 時〜
    P = hr(np.array([c[f"{k:04d}_PREC"] for k in range(1, NMEM + 1)]))
    pd = hr(c[f"{NMEM + 1:04d}_PREC"])
    out = {}
    for nm, ((a, b), _) in TARGETS.items():
        out[nm] = (P[:, a - T0:b - T0].sum(axis=1), pd[a - T0:b - T0].sum())
    return out


def masks():
    """目標のパッチと、周りの 8 パッチの格子（NY, NX の bool）。二重周期。"""
    P = mp.PATCH
    tgt = np.zeros((mp.NY, mp.NX), bool)
    tgt[J0:J0 + K, I0:I0 + K] = True
    blk = np.zeros_like(tgt)
    jj = np.arange(J0 - P, J0 + K + P) % mp.NY
    ii = np.arange(I0 - P, I0 + K + P) % mp.NX
    blk[np.ix_(jj, ii)] = True
    return tgt, blk & ~tgt


def increments(X, Y, ystar):
    """X（member, NY, NX）、Y（member）から、full・local の修正量（NY, NX）と途中の量。"""
    tgt, ring = masks()
    Xa = X - X.mean(axis=0)
    Ya = Y - Y.mean()
    sy2 = Ya.var(ddof=1)
    gain = (ystar - Y.mean()) / (sy2 + sy2)                      # (y* − Ȳ) / (σ_Y² + σ_R²)、σ_R = σ_Y
    cov = np.tensordot(Ya, Xa, axes=(0, 0)) / (len(Y) - 1)
    full = cov * gain
    z = np.stack([X[:, tgt].mean(axis=1), X[:, ring].mean(axis=1)], axis=1)   # (member, 2)
    za = z - z.mean(axis=0)
    dz = (Ya @ za) / (len(Y) - 1) * gain
    local = np.zeros_like(full)
    local[tgt], local[ring] = dz[0], dz[1]
    b = np.linalg.lstsq(np.c_[np.ones(len(Y)), z], Y, rcond=None)[0][1:]   # Y の (z_T, z_S) への重回帰
    r = [np.corrcoef(z[:, k], Y)[0, 1] for k in range(2)]
    return full, local, dict(b=b, r=np.array(r), sy=np.sqrt(sy2), ybar=Y.mean(), gain=gain, dz=dz)


def predict(d, b):
    """修正量 d の、目標のパッチ・周りの 8 パッチの平均からの線形の予測 ΔY。"""
    tgt, ring = masks()
    return b[0] * d[tgt].mean() + b[1] * d[ring].mean()


def shift_random(d, rng):
    """d を、パッチ単位のランダムなずらし（目標のパッチとその周りに重ならない位置）で動かす。"""
    n = mp.NY // mp.PATCH
    while True:
        sj, si = rng.integers(0, n, 2)
        if min(sj, n - sj) >= 3 or min(si, n - si) >= 3:          # 3×3 パッチどうしが重ならない
            return np.roll(np.roll(d, sj * mp.PATCH, 0), si * mp.PATCH, 1), (int(sj), int(si))


def main():
    dry = os.environ.get("DRY") == "1"
    pz = np.load(f"{ENS}/perturbation.npz")
    X = np.array([pz[f"{k:04d}"] for k in range(1, NMEM + 1)])
    ys = target_y()
    rng = np.random.default_rng(SEED)
    tgt, ring = masks()
    runs = {"none": np.zeros((mp.NY, mp.NX))}
    info = {}
    for nm, ((a, b), ystar) in TARGETS.items():
        Y, ymd = ys[nm]
        full, local, s = increments(X, Y, ystar)
        rank = (Y < ymd).sum()
        print(f"\n== {nm}: {a}〜{b} 時の雨。y* = {ystar} mm、Ȳ = {s['ybar']:.3f}、σ_Y = {s['sy']:.3f}、"
              f"mdet {ymd:.3f}（80 member 中 小さいほうから {rank} 番目）")
        print(f"   相関: 目標のパッチ {s['r'][0]:+.2f}、周りの 8 パッチ {s['r'][1]:+.2f}。"
              f"重回帰の傾き b_T {s['b'][0]:+.1f}、b_S {s['b'][1]:+.1f} mm/(m³/m³)")
        for an, d in [("full", full), ("local", local)]:
            for cl in ["clip", "noclip"]:
                dd = np.maximum(d, 0.0) if cl == "clip" else d
                key = f"{nm}_{an}_{cl}"
                runs[key] = dd
                info[key] = predict(dd, s["b"])
                print(f"   {an:5s} {cl:6s}: 目標のパッチ {dd[tgt].mean():+.5f}、周り {dd[ring].mean():+.5f}、"
                      f"外 |Δθ| の平均 {np.abs(dd[~(tgt | ring)]).mean():.5f}、最大 {dd.max():+.5f}、最小 {dd.min():+.5f}  "
                      f"予測 ΔY {info[key]:+.3f} mm")
        key = f"{nm}_random"
        runs[key], sh = shift_random(runs[f"{nm}_local_clip"], rng)
        info[key] = predict(runs[key], s["b"])
        print(f"   random: local・clip を パッチ {sh} ずらす。予測 ΔY {info[key]:+.3f} mm")
        info[f"{nm}_stats"] = s
    if dry:
        return

    if os.path.exists(f"{OUT}/init"):
        sys.exit(f"{OUT}/init がすでにあります（作り直すときは消す）。")
    mp.OUT = OUT
    names = list(runs)
    applied = {}
    for k, key in enumerate(names, start=1):
        m = f"{k:04d}"
        applied[key] = mp.make_init(m, f"{mp.SRC}/{mp.T_INT}/anal/mdet", runs[key] if key != "none" else None)
        mp.make_conf(m)
        print(f"{m}: {key}", flush=True)
    with open(f"{OUT}/work/launcher.conf", "w") as f:
        f.write(f"""&PARAM_ENSEMBLE
MEMBER = {len(names)},
MEMBER_RUN = {len(names)},
CONF_FILES = "<member>/run.d<domain>_{mp.T_INT}.conf",
CONF_FILES_SEQNUM = .false.,
DET_RUN = .false.,
EFSO_RUN = .false.,
/

&PARAM_PROCESS
PPN = 4,
MEM_NODES = 36,
NUM_DOMAIN = 1,
PRC_DOMAINS = 144,
/
""")
    np.savez_compressed(f"{OUT}/control.npz", names=np.array(names), targets=np.array(list(TARGETS)),
                        **{f"inc_{k}": runs[k] for k in names}, **{f"applied_{k}": applied[k] for k in names},
                        **{f"pred_{k}": v for k, v in info.items() if not k.endswith("_stats")},
                        **{f"{nm}_{q}": np.asarray(v) for nm in TARGETS for q, v in info[f"{nm}_stats"].items()})
    print(f"作った: {OUT}（{len(names)} 本）")


if __name__ == "__main__":
    main()
