# Phase 5 — cycle 設定の作成と ensemble forecast の接続：計画書から移した詳細

準備の計画書（`../20260923_experiment_plan.md`）を簡潔にしたとき（2026-11-06）に、そこから移した詳細。中身は書いた当時のまま。
パスはフォルダの整理（2026-11-06）の前のもの（`init/` → `setup/init/` など。対応は `convection/README.md`）。節の番号は、もとの計画書のもの。

## 経緯（もとの改訂履歴から）

  - Phase 5: history は rep_asakura の 108 項目に同化で必要な 5 項目を加えた 113 項目、10 分ごと（`FCSTOUT = 600`）。
    `config.rc` の `SCRP_DIR` を `$DIR/convection` にした（`run/` の設定が使われる不具合の修正）。MEMBER = 20 で step 1–3 を確認

## 進捗のチェックリスト（もとの「進捗状況」から）

- [x] Phase 5 — cycle 設定の作成と ensemble forecast の接続 — 2026-09-25
  - [x] `config.main.Wisteria`, `config.cycle`, `config.nml.*` の作成 — 2026-09-25（`docs/phase5/config_notes.md`）
  - [x] step 1–3（MEMBER=2） — 2026-09-25（16 秒。0001 は Phase 3 と完全一致。`docs/phase5/config_notes.md`）
  - [x] step 1–3（MEMBER=20） — 2026-09-25（large-o、25 秒。22 本すべて正常）

## Phase 5 の手順（もとの 5 節）

- 4 節の分類に従って `config.main.Wisteria`, `config.cycle`, `config.nml.*` を作る。
- まず `MEMBER=2`（144 ノード, debug-o）で `ISTEP=1`, `FSTEP=3` を実行し、step 1–3 の設定を確認する。
- 次に `MEMBER=20`（792 ノード, large-o）で同じ範囲を実行する。

### 完了条件

`$OUTDIR/<STIME+1h>/gues/` に 0001–0020 と mdet の forecast が出力される。
