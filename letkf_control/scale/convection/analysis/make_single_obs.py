#!/usr/bin/env python3
"""1 点観測試験（Phase 7d、7c の ②）の観測ファイルを作る。

基準の観測 result/obs/obs_<T>.dat から、互いに局所化の打ち切り（HORI_LOCAL 20 km × 3.65 ≈ 73 km）より離れた 4 つの柱
（格子番号 (28, 28)・(28, 88)・(88, 28)・(88, 88)、互いに 120 km。二重周期でも 120 km）で、指定した要素の観測を 1 つずつ選ぶ。
それぞれの点の局所解析には、その観測 1 つだけが効く。

選び方: C' の obsdep（同じ時刻、QC を通った観測）で、気圧が PMIN〜PMAX の中から、|O−B| が 0.2〜0.45（QC の 0.5 未満）で
目標の気圧 PTARGET にいちばん近いもの。観測の値・誤差は基準の観測そのまま（レコードをそのままコピー）。

出力: <OUTDIR>/obs_<T>.dat（4 レコード）・controltarget（基準のコピー）・single_obs.txt（選んだ観測の一覧）
使い方: python3 make_single_obs.py <要素 U|T> <出力ディレクトリ> [時刻（既定 20000131060000）]
"""
import os
import shutil
import sys

import numpy as np

import common as cm

COLS = [(28, 28), (28, 88), (88, 28), (88, 88)]
PTARGET, PMIN, PMAX = 700.0, 550.0, 850.0
ELM = {"U": 2819, "V": 2820, "T": 3073}


def main():
    name, out = sys.argv[1], sys.argv[2]
    t = sys.argv[3] if len(sys.argv) > 3 else "20000131060000"
    src = f"{cm.OUTDIR}/obs/obs_{t}.dat"
    raw = np.fromfile(src, dtype="<i4").reshape(-1, 10)
    obs = cm.read_obs(src)
    dep = cm.read_obsdep(f"{cm.OUTDIR}/../sens/Cp/obsdep/obsdep_{t}.dat") if os.path.isdir(f"{cm.OUTDIR}/../sens/Cp") \
        else cm.read_obsdep(f"{cm.OUTDIR}/obsdep/obsdep_{t}.dat")
    lon, lat, _ = cm.read_global(cm.hist_dir("mdet", cm.tprev_of(t)))
    jj, ii, _ = cm.nearest_column(lon, lat, obs[:, 1], obs[:, 2])
    djj, dii, _ = cm.nearest_column(lon, lat, dep[:, 1], dep[:, 2])
    pick = []
    lines = []
    for j, i in COLS:
        cand = np.flatnonzero((dep[:, 0] == ELM[name]) & (djj == j) & (dii == i) & (dep[:, 3] >= PMIN) & (dep[:, 3] <= PMAX)
                              & (np.abs(dep[:, 9]) >= 0.2) & (np.abs(dep[:, 9]) <= 0.45))
        if len(cand) == 0:
            sys.exit(f"柱 ({j}, {i}) に条件に合う {name} の観測がありません。")
        m = cand[np.argmin(np.abs(dep[cand, 3] - PTARGET))]
        n = np.flatnonzero((obs[:, 0] == ELM[name]) & (jj == j) & (ii == i) & (np.abs(obs[:, 3] - dep[m, 3]) < 0.01))
        if len(n) != 1:
            sys.exit(f"柱 ({j}, {i}) の観測を観測ファイルで 1 つに決められません（{len(n)} 個）。")
        pick.append(n[0])
        lines.append(f"{name} 格子 ({j}, {i}) 経度 {obs[n[0], 1]:.5f} 緯度 {obs[n[0], 2]:.5f} 気圧 {obs[n[0], 3]:.2f} hPa "
                     f"観測 {obs[n[0], 4]:.4f}  C' の O−B {dep[m, 9]:+.4f}  第一推定のばらつき {dep[m, 11]:.4f}")
    os.makedirs(out, exist_ok=True)
    raw[pick].tofile(f"{out}/obs_{t}.dat")
    shutil.copyfile(f"{cm.OUTDIR}/obs/controltarget", f"{out}/controltarget")
    with open(f"{out}/single_obs.txt", "w") as f:
        f.write("\n".join(lines) + "\n")
    print("\n".join(lines))
    print(f"出力: {out}/obs_{t}.dat（{len(pick)} 個）")


if __name__ == "__main__":
    main()
