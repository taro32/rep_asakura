# Phase 3 — 単独 forecast と実行時間の計測：計画書から移した詳細

準備の計画書（`../20260923_experiment_plan.md`）を簡潔にしたとき（2026-11-06）に、そこから移した詳細。中身は書いた当時のまま。
パスはフォルダの整理（2026-11-06）の前のもの（`init/` → `setup/init/` など。対応は `convection/README.md`）。節の番号は、もとの計画書のもの。

## 経緯（もとの改訂履歴から）

  - Phase 3: 1 member × 1 時間の予報が 21 秒と判明。48 cycle を 1 ジョブ・`TIME_LIMIT = 12:00:00` で流す。
    debug-o を `config.main.Wisteria` の `RSCGRP` で切り替えられるようにした（`cycle_run.sh`）

## 進捗のチェックリスト（もとの「進捗状況」から）

- [x] Phase 3 — 単独 forecast と実行時間の計測 — 2026-09-25
  - [x] 1 member × 1 時間の実行時間 — 2026-09-25（21 秒。`docs/phase3/fcst1h_result.md`）
  - [x] 1 cycle の所要時間の見積もりと `TIME_LIMIT`・ジョブ分割の方針 — 2026-09-25（数分／cycle。1 ジョブ・TIME_LIMIT 12 時間。debug-o を切り替え可能に）

## Phase 3 の手順と結果（もとの 5 節）

- `config.nml.scale` と同じ物理設定で、1 member（rep_asakura の `1/` の初期値）を 1 時間積分する（debug-o, 36 ノード）。
- 1 時間積分にかかる実時間を記録し、1 cycle の所要時間を見積もる。
  step 7 は step 3 と同じく全 member の予報をやり直すので、1 cycle は「予報 2 回 + LETKC + obsmake + LETKF」になる（`docs/phase1/dependency.md` 4.4 節）。
- 24 cycle を 1 ジョブ（80 member は x-large-o、最大 24 時間）で流せるかを判断し、`TIME_LIMIT` を決める。
- 動作確認に debug-o（最大 144 ノード・30 分）を使うかを決める。
  1 cycle が 30 分に収まるなら、`convection/cycle_run.sh` の `rscgrp=regular-o` を `config.main.Wisteria` から切り替えられるようにする。
  収まらないなら regular-o のまま使う（`docs/phase1/dependency.md` 4.5 節）。

### 結果と決定（2026-09-25）

記録は `docs/phase3/fcst1h_result.md`。

- 1 member × 1 時間の予報は **21 秒**で正常終了した。対流が発生し、値も妥当（図は `docs/phase3/figs/`）。
- 80 member・10 km の 1 cycle は約 10 分（24 cycle で 3:56）。
- **ジョブ分割**: 24 cycle を 1 ジョブで流す。**`TIME_LIMIT = 12:00:00`**（`config.cycle` に書く。2 cycle の試験の実績を見て調整する）。
- **rscgrp**: debug-o を使えるようにする。`convection/cycle_run.sh` の `#PJM -L "rscgrp=regular-o"` を
  `#PJM -L "rscgrp=${RSCGRP:-regular-o}"` に変えた（`run/` からの唯一の変更）。
  `config.main.Wisteria` で `RSCGRP=debug-o` とすれば debug-o、書かなければ regular-o になる。
- **単独実行の出力の置き方**: history・refstate・restart を種類ごと・member ごとに分ける
  （例: `$OUTDIR/phase3_fcst1h/history/1/`）。cycle の出力は framework が `<time>/{anal,gues,hist}/<member>/` に分けるので、そちらは変えない。
- **history の量**: 今の設定（60 秒ごと・108 項目）のままだと cycle 全体で約 7 TB になり、ディスクの空きを超える。Phase 5 で絞る。

### 完了条件

1 cycle あたりの所要時間の見積もり、ジョブ分割の方針、動作確認に使う rscgrp が決まっている。
