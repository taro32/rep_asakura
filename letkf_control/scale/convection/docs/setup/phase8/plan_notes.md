# Phase 8 — 1 cycle → 2 cycle → 24 時間：計画書から移した詳細

準備の計画書（`../20260923_experiment_plan.md`）を簡潔にしたとき（2026-11-06）に、そこから移した詳細。中身は書いた当時のまま。
パスはフォルダの整理（2026-11-06）の前のもの（`init/` → `setup/init/` など。対応は `convection/README.md`）。節の番号は、もとの計画書のもの。

## 経緯（もとの改訂履歴から）

    - 流し方（2026-10-28 決定）: 感度実験と同じく 1,476 ノード（41 × 36）で、member を 2 回に分けて順に流す。
      (80 + 2) × 36 = 2,952 ノードは最大の x-large-o（2,304 ノード）にも入らないため。rscgrp は `regular-o` のまま（ノード数で x-large-o に振り分けられる。最大 24 時間）。
      24 cycle で 3:56 だった（感度実験 M80L10_24、`HIST_CLEAN=1`）
    - LETKC（制御）の局所化半径（`config.nml.letkc` の `HORI_LOCAL`、今は仮の 20 km）は、**制御を実施する際に考える**（2026-10-28 決定）。
      LETKF とは別の設定ファイルで、連動しない。同化の局所化（偶然の相関を切る）と制御半径（修正を許す範囲）は役割が違うので、
      LETKF の 10 km にそろえるとは限らない。Phase 9-1 の「制御半径」で扱う
    - 設定ファイルを変更した（2026-10-28）: `config.main.Wisteria` の `MEMBER` の既定を 20 → 80。`NNODES` は x-large-o の最大（2,304）を超えるときだけ
      半分（切り上げ）にする式を足した（80 member → 1,476 ノード。20 member は 792 のまま）。`config.nml.letkf` の `HORI_LOCAL` を 2.0D4 → 1.0D4。
      感度実験（`sens/submit.sh`）は `SENS_MEMBER` を毎回渡すので影響しない。`config.nml.letkc` は変えていない
    - **本番の OUTDIR を `result/` → `result_m80/` に変えた**（2026-10-28、`config.main.Wisteria`）。`result/` は 20 member・6 cycle の基準実験（ジョブ 9844986）で、
      感度実験の観測（`result/obs`）と評価の真値（`result/` の mdet）に使っているので残す。`analysis/common.py` の `OUTDIR` の既定は `result/` のまま
    - 80 member の初期値 `init_soil_m80` を `result_m80/20000131000000/anal/` に取り込んだ（2026-10-28、ジョブ 10081978、9:50。`$BASE/import_m80_job.sh`、出力 `$BASE/import_m80.out`）。
      **82 個（0001〜0080・mdet・mean）× 144 ファイル、すべて md5 が一致**。`result_m80/` は約 17 GB。
      `init/import_rep_asakura.sh` を `NMEM=80 MDET_SRC=81` で使い、md5 を照合。controltarget（制御なし）も `result/obs` から `result_m80/obs/` にコピーする。
      `init_soil_m80` の 1〜20 番と mdet（81 番）は、20 member の初期値（`init_soil_20261003` の 1〜20・21 番）と同じファイル
    - 未定: 本番を流す前に、ディスク（グループの空き約 4.9 TB、2026-10-28）に収まるかを見積もる。収まらなければ `HIST_CLEAN=1`（member の history を各 cycle の後に消す）にする。
      ただし member ごとの降水を見るには member の history が要る（下の 2026-10-28 の項）
- 2026-10-28: **本番の cycle 期間を 48 時間 → 24 時間（24 cycle）に短くする**（ユーザー）。
  - 理由: 誤差は 7〜10 時間で横ばいになり（B-1、`docs/phase7d/sens/compare_obspoint_long.png`）、24 時間で十分。介入（制御）には 6〜9 時間あたりがよさそうで、
    12 時間以降はだいぶ落ち着いている。実行時間（80 member で約 4 時間）とディスクも半分で済む
  - 本番のジョブの最初の確認: **member ごとの降水がばらけているか**（「すべての道が豪雨に通じていないか」）。
    member を領域平均の積算降水 ΣP（12〜24 時間）で並べ、大きい・真ん中・小さい member を 2 つずつ、地図で比べる（ユーザー）。
    色の段は全 member の格子点の積算降水の分布（分位点）から決める。`analysis/plot_member_prec.py`（`member_prec_<H0>-<H1>h.png`・`_sorted.png`）。
    基準実験（`result/`、20 member・0〜6 時間）で動くことを確かめた（読み込みに約 5 分半）
  - 2 cycle のテスト（ジョブ 10083036）は、開始前に取り消した。ステージングで `result_m80/20000131010000`・`20000131020000` などの空のディレクトリができたが、0 時の初期値は変わっていない
  - **本番を投入した**（2026-10-28 19:34、ジョブ 10083341、x-large-o、開始予定 10/29 7:00）。tmux `run24`（wisteria05）で
    `cycle_run.sh 20000131000000 20000131230000 1 10 static 08:00:00`。`HIST_CLEAN=0`（member の history を残す。約 2.6 TB）。ログ `result_m80/run24_cycle_run.log`。
    `config.cycle` の `ETIME` を `20000131230000`（最後の cycle の開始時刻。前の `20000202000000` は 49 cycle になる値だった）、`TIME_LIMIT` を 08:00:00 にした
  - 終わったら `result_m80/after_run24.sh`（このセッションのバックグラウンド）が 24 cycle がそろったかを確かめ、図のジョブ（`analysis/plot_member_prec_job.sh`、Aquarius）を投げる。
    出力は `docs/phase8/run24_m80/`。Wisteria は 2026-10-30（金）9:00 から計画停止なので、図は停止前にこのセッションから `SendUserFile` でユーザーに送る

## 進捗のチェックリスト（もとの「進捗状況」から）

- [ ] Phase 8 — cycling
  - [x] 1 cycle — 2026-10-03（step 1–10 全体。ジョブ 9804836 など）
  - [x] 2 cycle（時刻・restart の引き継ぎの整合）— 2026-10-03（6 cycle で確認。ジョブ 9805795）
  - [ ] 24 時間（80 member・10 km、`result_m80/`。2026-10-28 に 48 時間から変更）

## Phase 8 の手順（もとの 5 節）

1. `ETIME = STIME + 1h` で 1 cycle 全体。
2. `ETIME = STIME + 2h` で 2 cycle。analysis → 次 cycle の restart、mdet の引き継ぎ、
   観測・controltarget・history・LETKC 入出力の時刻の整合を確認する。
3. 24 cycle で本実行（2026-10-28 に 48 時間から変更）。`TIME_LIMIT` は Phase 3 と 2 cycle の実績から設定する
   （必要なら複数ジョブに分割する）。
