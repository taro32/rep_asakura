# analysis/ — 結果の確認・図のスクリプト

2026-10-14 に `docs/phase7/`・`docs/phase7d/`・`phase3/` から集めた。共通の部品は `common.py` にまとめた。
記録（.md）と、その記録が参照する図・`.out` は `docs/` に置く。

## 共通の約束

- 実行はこのディレクトリで行う（`cd analysis`）。各スクリプトは `common.py` を import する。
- 読む結果は環境変数で指定する。
  - `OUTDIR`: 結果の場所（既定 `/work/gv42/v42013/20260923_enkc_convection/result`。退避した結果は `result/bak_…`）
  - `STIME`: 1 cycle 目の開始時刻（既定 `20000101000000`。Phase 7d は `20000131000000`）
- 図を出すスクリプトの一部は、出力先 `FIGDIR` が必須（前の結果を上書きしないため）。
  特定の実行専用の図のスクリプト（`plot_*.py`）は、出力先がその実行の記録の場所に固定されている。

## スクリプト

| スクリプト | 内容 | 出力 |
| --- | --- | --- |
| `common.py` | 共通部品: 読み込み（history・restart・観測）、観測演算子、物理量への変換、sprd の読み替え、図のフォント・色 | — |
| `check_obsmake.py` | 7a: 観測と mdet の 60 分の予報の照合（O − H(mdet) の標準偏差が観測誤差 0.1 か） | 標準出力 |
| `check_letkf.py` | 7b: mdet が LETKF で変わらないか、増分、ばらつき、観測地点での O−B・O−A | 標準出力 |
| `check_onset.py` | member ごとの対流の始まり（領域平均の雲・降水の時間変化） | 標準出力 |
| `check_members.py` | 真値（mdet）がアンサンブルの中にいるか（0 分・60 分） | 標準出力 |
| `check_truth.py` | 1 cycle の解析が真値に近づいたか（全格子点の RMSE とばらつき） | 標準出力、`FIGDIR/truth_*.png` |
| `check_cycles.py` | 複数 cycle の RMSE とばらつきの時間変化（`--fast` で U, V, W のばらつきを省く） | 標準出力、`FIGDIR/cycles_timeseries.png` |
| `check_obspoint.py` | 観測がある点だけで、第一推定・解析の平均と真値の差（ノイズを除いた値）を cycle ごとに比べる。QC を通った・捨てられた観測に分け、目安と全格子点も並べる | 標準出力、`FIGDIR/obspoint_*.png` |
| `check_spinup.py` | Phase 7d の 30 日スピンアップの平衡 | 標準出力、`FIGDIR/spinup_timeseries.png` |
| `offline_letkf.py` | 7b の原因調べ: LETKF の平均の更新を Python で再現し、設定を変えて比べる | 標準出力 |
| `plot_fcst1h.py` | Phase 3 の単独予報の図 | `docs/phase3/figs/` |
| `plot_1cycle.py` | Phase 7d の 1 cycle（ジョブ 9829615）のミーティング用の図 | `docs/phase7d/run_soil_1cycle/` |
| `plot_6cycle.py` | Phase 7d の 6 cycle（ジョブ 9844986）のミーティング用の図 | `docs/phase7d/run_soil_6cycle/` |
| `plot_summary.py` | 2026-10-07 のミーティング用の 1 枚（`plot_6cycle.py` を使う） | `docs/phase7d/meeting_20261007/` |

## 例

```bash
cd analysis
STIME=20000131000000 OUTDIR=/work/gv42/v42013/20260923_enkc_convection/result/bak_soil_1cycle_9829615 FIGDIR=../docs/phase7d/run_soil_1cycle python3 check_truth.py > ../docs/phase7d/run_soil_1cycle/check_truth.out
STIME=20000131000000 FIGDIR=../docs/phase7d/run_soil_6cycle python3 check_cycles.py --fast > ../docs/phase7d/run_soil_6cycle/check_cycles_fast.out
```
