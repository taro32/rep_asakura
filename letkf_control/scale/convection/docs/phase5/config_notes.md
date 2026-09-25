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

## 本番で変えるところ

| ファイル | 項目 | 動作確認 | 本番 |
| --- | --- | --- | --- |
| `config.main.Wisteria` | `MEMBER` | 2 | 20 |
| `config.main.Wisteria` | `RSCGRP` | debug-o | regular-o |
| `config.main.Wisteria` | `OBSIN` | case_tc 用（仮） | 2 km 格子用（Phase 7） |
