# convection — 土壌水分による対流性降雨の EnKC 制御の実験

rep_asakura の理想化実験（2 km・120 × 120 格子・全陸面・二重周期・バケツ型の土壌）の設定で、
case_tc の EnKC（LETKF + LETKC）の cycle を動かし、その上で土壌水分による対流性降雨の制御を調べる。

2026-11-06 に、**準備（setup、〜2026-10-29）** と **制御（control、2026-11-02〜）** を別のフェーズとしてフォルダを分けた。

## 全体の流れ

```text
[準備 setup/]
  rep_asakura の初期値の取り込み（setup/init/import_rep_asakura.sh）
        ↓
  30 日のスピンアップ（setup/spinup/）
        ↓
  土壌水分の摂動を入れたアンサンブルの初期値（setup/init/perturb_soil.py・make_m80.sh。80 member + mdet）
        ↓
[本体]
  cycle（cycle_run.sh。毎時 LETKF で同化。mdet が真値、観測は mdet の予報 + ノイズ）
        ↓
[制御 control/]
  cycle の結果（result_m80）から、制御の実験をする
```

## フォルダ

| 場所 | 中身 |
| --- | --- |
| `cycle_run.sh`・`fcst_run.sh`・`config.*`・`src/`・`dat/` | **本体**（case_tc から移植した cycle の仕組み）。`config.main` は `config.main.Wisteria` へのリンク |
| `make_obsin/` | **本体の入力**: 擬似観測の位置（`obsin/`）と LETKC の制御の目標（`controltarget/`）。`config.main.Wisteria` が読む |
| `setup/` | **準備**（〜2026-10-29）。`init/` 初期値、`spinup/` スピンアップ、`phase3_timing/` 単独予報の時間の計測、`phase7d_sens/` 同化の感度実験 |
| `control/` | **制御**（2026-11-02〜）の実験の入力とジョブ。`<日付>_<目的>/`（日付は始めた日） |
| `analysis/` | 解析のスクリプト。`setup/phase<N>/` と `control/<日付>_<目的>/` に分けた（`analysis/README.md`） |
| `docs/` | 記録。`setup/`（準備の計画と経緯の要約 `20260923_experiment_plan.md`、phase0〜phase8 の記録と補足ノート `plan_notes.md`）、`control/`（`notes.md` と結果の図、`tex/`）、`tex/template.tex`（tex の雛形） |

計算の結果は `/work/gv42/v42013/20260923_enkc_convection/` にある（`result_m80/` が Phase 8 の 24 時間の cycle、
`phase9_patch_t08/`・`phase9_control_t08/` が制御の実験）。名前はフォルダの整理の前のまま。

## 旧パス → 新パス（2026-11-06 の整理）

`docs/setup/` の中の記録は書き換えていないので、古いパスが残っている。次のように読み替える。

| 旧 | 新 |
| --- | --- |
| `init/` | `setup/init/` |
| `spinup/` | `setup/spinup/` |
| `phase3/` | `setup/phase3_timing/` |
| `sens/` | `setup/phase7d_sens/` |
| `phase9/patch_fcst/` | `control/20261103_patch_fcst/` |
| `phase9/control/` | `control/20261103_enkc_once/` |
| `analysis/check/`・`plot/`・`tools/` の準備の分 | `analysis/setup/phase3/`・`phase7/`・`phase7d/`・`phase8/` |
| `analysis/check/`・`plot/` の制御の分 | `analysis/control/20261102_target/`・`20261102_soil_cov/`・`20261103_patch_fcst/`・`20261103_enkc_once/` |
| `docs/phase0/`〜`docs/phase8/`・`docs/env/` | `docs/setup/phase0/`〜`docs/setup/phase8/`・`docs/setup/env/` |
| `docs/20260923_experiment_plan.md` | `docs/setup/20260923_experiment_plan.md` |
| `docs/phase9/phase9_notes.md` | `docs/control/notes.md` |
| `docs/phase9/<結果>/` | `docs/control/<日付>_<結果>/`（target_prec・target_bowen・soil_cov・soil_track は 20261102、soil_cov_all・patch_fcst は 20261103、control は `20261103_enkc_once`） |
| `docs/tex/phase7d_summary.*` | `docs/setup/tex/` |
| `docs/tex/enkc_variance.*`・`phase9_week.*` | `docs/control/tex/`（`phase9_week` は `20261104_summary` に改名） |
