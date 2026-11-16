# analysis/ — 結果の確認・図のスクリプト

2026-10-14 に `docs/phase7/`・`docs/phase7d/`・`phase3/` から集めた。共通の部品は `common.py` にまとめた。
2026-11-06 に、準備（`setup/`、〜2026-10-29）と制御（`control/`、2026-11-02〜）に分け、その中を phase・目的ごとのフォルダにした。
記録（.md）と、その記録が参照する図・`.out` は `docs/` に置く。

## 共通の約束

- 実行はこのディレクトリで行う（`cd analysis` して `python3 setup/phase7/check_truth.py` のように呼ぶ）。
- 置き場所:
  - `setup/phase<N>/` モデルの準備（cycle を動かすまで。〜2026-10-29）の確認・図。phase の番号は `docs/setup/20260923_experiment_plan.md` のもの
  - `control/<日付>_<目的>/` 制御の実験（2026-11-02〜）の解析。日付は始めた日。記録は `docs/control/notes.md`、図は `docs/control/<日付>_<目的>/`
  - ファイル名の頭で種類を分ける: `check_` 確認（数値・表が主）、`plot_` 図、`make_` 実験の入力を作るもの。`_job.sh` は Aquarius で流すジョブ
- 各スクリプトは 2 つ上の `common.py` を import する（同じフォルダ以外のスクリプトを使うものは、そのフォルダも `sys.path` に足している）。
- 読む結果は環境変数で指定する。
  - `OUTDIR`: 結果の場所（既定 `/work/gv42/v42013/20260923_enkc_convection/result`。退避した結果は `result/bak_…`）
  - `STIME`: 1 cycle 目の開始時刻（既定 `20000101000000`。Phase 7d は `20000131000000`）
- 図を出すスクリプトの一部は、出力先 `FIGDIR` が必須（前の結果を上書きしないため）。
  特定の実行専用の図のスクリプト（`plot_*.py`）は、出力先がその実行の記録の場所に固定されている。

## スクリプト（準備: setup/）

| スクリプト | 内容 | 出力 |
| --- | --- | --- |
| `common.py` | 共通部品: 読み込み（history・restart・観測）、観測演算子、物理量への変換、sprd の読み替え、図のフォント・色 | — |
| `setup/phase7/check_obsmake.py` | 7a: 観測と mdet の 60 分の予報の照合（O − H(mdet) の標準偏差が観測誤差 0.1 か） | 標準出力 |
| `setup/phase7/check_letkf.py` | 7b: mdet が LETKF で変わらないか、増分、ばらつき、観測地点での O−B・O−A | 標準出力 |
| `setup/phase7/check_onset.py` | member ごとの対流の始まり（領域平均の雲・降水の時間変化） | 標準出力 |
| `setup/phase7/check_members.py` | 真値（mdet）がアンサンブルの中にいるか（0 分・60 分） | 標準出力 |
| `setup/phase7/check_truth.py` | 1 cycle の解析が真値に近づいたか（全格子点の RMSE とばらつき） | 標準出力、`FIGDIR/truth_*.png` |
| `setup/phase7/check_cycles.py` | 複数 cycle の RMSE とばらつきの時間変化（`--fast` で U, V, W のばらつきを省く） | 標準出力、`FIGDIR/cycles_timeseries.png` |
| `setup/phase7d/check_obspoint.py` | 観測がある点だけで、第一推定・解析の平均と真値の差（ノイズを除いた値）を cycle ごとに比べる。QC を通った・捨てられた観測に分け、目安と全格子点も並べる | 標準出力、`FIGDIR/obspoint_*.png` |
| `setup/phase7d/check_spinup.py` | Phase 7d の 30 日スピンアップの平衡 | 標準出力、`FIGDIR/spinup_timeseries.png` |
| `setup/phase7/offline_letkf.py` | 7b の原因調べ: LETKF の平均の更新を Python で再現し、設定を変えて比べる | 標準出力 |
| `setup/phase7d/check_bias.py` | 解析の誤差を領域平均の偏りと、偏りを除いた部分に分ける（P・T・U・QV） | 標準出力 |
| `setup/phase7d/check_scales.py` | 誤差を水平の波長の帯に分けて、同化あり・なしを比べる（B-2） | 標準出力、`FIGDIR/scales_<組>.png`・`.npz` |
| `setup/phase7d/check_single_obs.py` | 1 点観測試験（S1U・S1T）の O−A / O−B を理論値と比べ、観測のまわりの修正を描く | 標準出力、`docs/setup/phase7d/sens/single_obs_*.png` |
| `setup/phase7d/compare_sens.py` | 感度実験の評価結果（`check_cycles.py --fast`・`check_obspoint.py` の `.out`）を並べて比べる | 標準出力、`docs/setup/phase7d/sens/compare_*.png` |
| `setup/phase7d/toy_kf.py` | 同化の誤差の時間変化を、スカラーのカルマンフィルタで確かめる（`docs/setup/phase7d/theory_da_error.md` の付録） | 標準出力、`toy_kf.png`（カレントディレクトリ） |
| `setup/phase3/plot_fcst1h.py` | Phase 3 の単独予報の図 | `docs/setup/phase3/figs/` |
| `setup/phase7d/plot_1cycle.py` | Phase 7d の 1 cycle（ジョブ 9829615）のミーティング用の図 | `docs/setup/phase7d/run_soil_1cycle/` |
| `setup/phase7d/plot_6cycle.py` | Phase 7d の 6 cycle（ジョブ 9844986）のミーティング用の図 | `docs/setup/phase7d/run_soil_6cycle/` |
| `setup/phase7d/plot_summary.py` | 2026-10-07 のミーティング用の 1 枚（`plot_6cycle.py` を使う） | `docs/setup/phase7d/meeting_20261007/` |
| `setup/phase8/plot_member_prec.py` | Phase 8 の 24 時間の、member ごとの積算降水（ジョブは `setup/phase8/plot_member_prec_job.sh`） | `FIGDIR/member_prec_*.png`・`.npz` |
| `setup/phase8/check_mdet_rank.py` | Phase 8 の追加検証（2026-11-07）: mdet が 80 member の中で何番目か（目標領域の降水・逐次の制御の Y・土壌水分 0〜20 cm、0〜24 時）。`docs/control/20261102_soil_track/soil_track.npz` を読む | `docs/setup/phase8/mdet_rank/` |
| `setup/phase7d/make_single_obs.py` | 1 点観測試験の観測ファイルを、基準の観測から作る | `<出力ディレクトリ>/obs_<T>.dat` ほか |

## スクリプト（制御: control/）

| スクリプト | 内容 | 出力 |
| --- | --- | --- |
| `control/20261102_target/plot_target_prec.py` | 目標領域（x 70〜90 km・y 110〜130 km）の雨の時間変化（Phase 8 の 80 member） | `docs/control/20261102_target_prec/` |
| `control/20261102_target/plot_target_bowen.py` | 目標領域の地表フラックス・ボーエン比・境界層の高さ | `docs/control/20261102_target_bowen/` |
| `control/20261102_soil_cov/check_soil_cov.py` | Phase 8 の土壌水分と目標領域の雨の共分散（7〜12 時） | `docs/control/20261102_soil_cov/` |
| `control/20261102_soil_cov/check_soil_cov_all.py` | 同じく 0〜12 時のすべての時刻（2026-11-03） | `docs/control/20261103_soil_cov_all/` |
| `control/20261102_soil_cov/plot_soil_track.py` | 土壌水分のばらつきの層ごとの時間変化と水の収支 | `docs/control/20261102_soil_track/` |
| `control/20261103_patch_fcst/check_patch_fcst.py` | 8 時にパッチの摂動を入れた予報: 目標領域の時系列、摂動と雨・ボーエン比の相関 | `docs/control/20261103_patch_fcst/` |
| `control/20261103_patch_fcst/check_patch_lcl.py` | 同じ予報の LCL・境界層の高さと降り始め | `docs/control/20261103_patch_fcst/patch_lcl.*` |
| `control/20261103_patch_fcst/check_patch_bowen_map.py` | 同じ予報の格子ごとのボーエン比の相関の地図（2026-11-04） | `docs/control/20261103_patch_fcst/patch_bowen_map_*` |
| `control/20261103_enkc_once/check_control.py` | 8 時に 1 回の EnKC の制御実験（11 本）の評価 | `docs/control/20261103_enkc_once/` |
| `control/20261107_mpc_soil/check_letkc_ctl_test.py` | LETKC の制御目標（要素 19001）の試験の検算: history から Y、y*・σ_R、ETKF の式で LAND_WATER の第 1・2 層の修正量を出し、anal − gues と比べる（2026-11-07） | 標準出力（試験の結果は `mpc_soil/<実験名>/check_letkc_ctl_test.txt`） |
| `control/20261107_mpc_soil/compare_mpc_soil.py` | MPC の本番（r080）と制御なし（nocontrol）の比較: 各 cycle の mdet・mean の予報し直しから目標領域の Y（t+45〜75 分）と t〜t+60 分の雨、obsdepcont から y*・σ_R・Ȳ（2026-11-07） | 標準出力、FIGDIR/mpc_target.png（結果は `docs/control/notes.md` 3.9） |

実験の入力を作るスクリプトとジョブは `convection/control/<日付>_<目的>/` にある（`make_patch_fcst.py`・`run_fcst.sh`・`make_control.py`）。

## 例

```bash
cd analysis
STIME=20000131000000 OUTDIR=/work/gv42/v42013/20260923_enkc_convection/result/bak_soil_1cycle_9829615 FIGDIR=../docs/setup/phase7d/run_soil_1cycle python3 setup/phase7/check_truth.py > ../docs/setup/phase7d/run_soil_1cycle/check_truth.out
STIME=20000131000000 FIGDIR=../docs/setup/phase7d/run_soil_6cycle python3 setup/phase7/check_cycles.py --fast > ../docs/setup/phase7d/run_soil_6cycle/check_cycles_fast.out
```
