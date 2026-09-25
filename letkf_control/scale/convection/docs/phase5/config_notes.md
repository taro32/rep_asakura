# Phase 5 — cycle 設定の作成（2026-09-25）

## 作った設定ファイル（`letkf_control/scale/convection/`）

| ファイル | 元 | 主な変更 |
| --- | --- | --- |
| `config.main.Wisteria` | `run/config/case_tc/config.main.Wisteria` | OUTDIR、`SCALE_NP_X/Y = 12`、`MEMBER = 2`（動作確認用）、`RSCGRP = debug-o`（動作確認用）、`TMPSUBDIR = convection`、SOUNDING、`OCEAN_INPUT = 0`、OBSIN（仮） |
| `config.main` | — | `config.main.Wisteria` へのシンボリックリンク（Phase 1 の 4.1 節。ファイルを 1 つにする） |
| `config.cycle` | `run/config/case_tc/config.cycle` | `STIME = 20000101000000`、`ETIME = 20000103000000`、`TIME_LIMIT = 12:00:00`、`FCSTOUT = 600` |
| `config.fcst` | `run/config/case_tc/config.fcst` | 変更なし（cycle では使わない。`cycle_run.sh` がコピーするので置いている） |
| `config.nml.scale` | `rep_asakura/run.conf` | 下記 |
| `config.nml.scale_init` | `init/init.conf_base` | 時刻・LOG・出力先を `!--XXX--` の目印に、静的入力を `convection/dat/` の絶対パスにした。cycle では実行されない |
| `config.nml.ensmodel` | `run/config.nml.ensmodel` | 変更なし |
| `config.nml.letkc`, `config.nml.letkf`, `config.nml.obsmake`, `config.obsmake` | `run/`・`run/config/case_tc/` | 変更なし（Phase 6・7 で見直す） |

### `config.nml.scale` の変更点（rep_asakura の `run.conf` から）

物理設定・格子・時間ステップ・history の項目は rep_asakura と同じ。

| 項目 | rep_asakura | convection |
| --- | --- | --- |
| 開始時刻・積分時間・restart の入出力・LOG・history の出力先・monitor の出力先 | 直接指定 | `!--XXX--` の目印（cycle スクリプトが値を入れる） |
| restart の出力間隔 | 10 日 | 目印（`LCYCLE` = 3600 秒が入る）。単位を `SEC` にした |
| 放射・陸面の入力 | `./PARAG.29` など | `convection/dat/` の絶対パス |
| history の出力間隔 | 60 秒 | 目印（`FCSTOUT` = 600 秒が入る） |
| history の項目 | 108 | **113**（LETKC・obsmake・LETKF が読む Umet, Vmet, SFC_PRES, U10m, V10m を追加） |
| `FILE_HISTORY_OUTPUT_SWITCH_*` | 1 日 | **外した**。付けるとファイル名に時刻が入り（`history_20000101-000100.000.pe*.nc`）、LETKC などが読む `history.pe*.nc` と合わなくなる |
| `FILE_HISTORY_OUTPUT_STEP0` | `.false.` | `.true.`（case_tc と同じ。初期時刻も出力する） |
| `ATMOS_REFSTATE_OUT_BASENAME` | 相対パスで出力 | **外した**（同化では使わない。相対パスだと作業ディレクトリに書かれる） |

### history の出力量の見込み

Phase 3 の実測（108 項目で 1 回あたり約 110 MB/member）から、10 分ごと（1 cycle に 7 回）・113 項目で
22 run × 48 cycle ≈ **0.9 TB**。

## 動作確認の手順（MEMBER = 2、debug-o）

`config.main.Wisteria` は動作確認用の値（`MEMBER=2`、`RSCGRP=debug-o`）になっている。

```bash
cd /work/02/gv42/v42013/scale-letkc/letkf_control/scale/convection
./cycle_run.sh 20000101000000 20000101000000 1 3 static 00:30:00
```

引数は `STIME ETIME ISTEP FSTEP CONF_MODE TIME_LIMIT`。1 cycle 分の step 1–3（step 1・2 は飛ばされるので、実際に動くのは step 3 のアンサンブル予報）を行う。

確認すること:

- `$OUTDIR/20000101010000/anal/{0001,0002,mean,mdet}/init_20000101-010000.000.pe*.nc` が出力される
- `$OUTDIR/20000101000000/hist/{0001,0002,mean,mdet}/history.pe*.nc` が出力され、時刻が 0, 10, …, 60 分の 7 回ある
- 113 項目が history に入っている

## 動作確認の記録

### 1 回目（2026-09-25 15:39、ジョブ 9718963）— 失敗

- ジョブは 2 秒で終了した。ジョブのログ（`$OUTDIR/exp/9718963_cycle_20000101000000/cycle_job.sh.9718963.out`）に
  `mpiexec -n 3264 ./scale-rm_ens ...` と `The specified number of processes is too many.` が出ていた。
- **原因:** ジョブ側で case_tc の設定（`MEMBER=100`、`tmp/tropicalcyclone`、OUTDIR = `20260603_enkc/result/case_tc`）が読まれていた。
  `config.rc` の `SCRP_DIR="$DIR/run"` が固定になっていて、`cycle_run.sh` が設定ファイルと `src/` を `run/` から TMP にコピーしていたため。
  投入側は `convection/config.main` を読むので、画面の表示（MEMBER=2 など）は正しく見えていた。
- **対処:** `convection/config.rc` の `SCRP_DIR` を `$DIR/convection` にした。
- **影響の確認:** case_tc の OUTDIR（`/work/gv42/v42013/20260603_enkc/result/case_tc`）に 15:39 以降に変更されたファイルはなかった。
  ジョブ側の作業領域 `tmp/tropicalcyclone` も存在しないまま（`cd` に失敗して止まった）。
- convection の OUTDIR には、投入側が作った空のディレクトリ（`20000101010000/` など）と `config/`・`exp/` が残っている。次の実行で使われるので、そのままにした。

### 2 回目（2026-09-25 15:45、ジョブ 9719033）— 成功

`SCRP_DIR` を直してから、同じコマンドで投入した。

| 確認したこと | 結果 |
| --- | --- |
| ジョブ | debug-o・144 ノード、経過 17 秒で正常終了（`SCALE-LETKF successfully completed`） |
| step の動き | step 1・2 は飛ばされ、step 3（アンサンブル予報）が 16 秒で終わった |
| ジョブ側の設定 | `$OUTDIR/exp/9719033_cycle_20000101000000/config.main` が convection のもの（`MEMBER=2`、`TMPSUBDIR=convection`） |
| 1 時間後の restart | `20000101010000/anal/{0001,0002,mean,mdet}/init_20000101-010000.000.pe*.nc` が各 144 ファイル |
| history | `20000101000000/hist/{0001,0002,mean,mdet}/history.pe*.nc` が各 144 ファイル。時刻は 0, 10, …, 60 分の 7 回。113 項目すべてある |
| 値 | NaN なし。値の範囲は Phase 3 と同じ |
| **0001 と Phase 3（member 1 の単独予報）** | **全変数で完全に一致**（DENS, MOMZ, RHOT, QV, QC, QR, LAND_WATER, LAND_TEMP の差の最大が 0） |
| mean と mdet | 完全に一致（どちらも `21/` の初期値から始めているので当然） |
| 0001 と 0002 | 異なる（別の member として計算されている） |

cycle の実行ファイル（`scale-rm_ens`）で回しても、Phase 3 の `bin/scale-rm` と同じ結果になった。

**history の量:** 4 member で 4.1 GB（1 member・1 cycle あたり約 1 GB）。
本番（22 run × 48 cycle）では約 **1.1 TB** になる（Phase 5 の見込み 0.9 TB より少し多い）。

## 本番で変えるところ

| ファイル | 項目 | 動作確認 | 本番 |
| --- | --- | --- | --- |
| `config.main.Wisteria` | `MEMBER` | 2 | 20 |
| `config.main.Wisteria` | `RSCGRP` | debug-o | regular-o |
| `config.main.Wisteria` | `OBSIN` | case_tc 用（仮） | 2 km 格子用（Phase 7） |
