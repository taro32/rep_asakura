# Phase 2 — convection/ の骨組み作成：計画書から移した詳細

準備の計画書（`../20260923_experiment_plan.md`）を簡潔にしたとき（2026-11-06）に、そこから移した詳細。中身は書いた当時のまま。
パスはフォルダの整理（2026-11-06）の前のもの（`init/` → `setup/init/` など。対応は `convection/README.md`）。節の番号は、もとの計画書のもの。

## 進捗のチェックリスト（もとの「進捗状況」から）

- [x] Phase 2 — convection/ の骨組み作成（framework・dat・init のコピー） — 2026-09-25

## ディレクトリ構成（もとの 1.2 節。整理の前の構成）

```text
letkf_control/scale/convection/
├── cycle_run.sh, fcst_run.sh, config.rc      ← run/ から複製
├── src/                                      ← run/src から複製
├── config.main.Wisteria                      ← 新規（OUTDIR・MEMBER=20・12×12 分割）
├── config.main -> config.main.Wisteria
├── config.cycle, config.fcst                 ← 新規（STIME・ETIME）
├── config.nml.scale, config.nml.scale_init   ← 新規（rep_asakura の run.conf / init.conf_base から）
├── config.nml.letkc, config.nml.letkf,
│   config.nml.obsmake, config.nml.ensmodel,
│   config.obsmake                            ← case_tc から複製して最小限変更
├── init/
│   ├── import_rep_asakura.sh                 ← 既存初期値を OUTDIR に取り込む
│   ├── ensinit.sh                            ← 初期値を OUTDIR に直接生成する版（再生成が必要な場合用）
│   ├── init.conf_base, init.sh_base          ← rep_asakura から（2 km・12×12 のまま）
│   └── ensperturb/                           ← env.txt, env_perturb1–21.txt, sounding_perturb.py
├── dat/                                      ← PARAG.29, PARAPC.29, VARDATA.RM29, cira.nc, MIPAS/, param.bucket.conf
├── make_obsin/                               ← controltarget・OBSIN 作成（2 km 格子用）
├── analysis/                                 ← 結果の確認・図のスクリプト（2026-10-14 に集約。共通部品は common.py、一覧は README.md）
└── docs/                                     ← 本書・各 Phase の記録（.md と、記録が参照する図・.out）

$OUTDIR = /work/gv42/v42013/20260923_enkc_convection/result（2026-09-25 確定・作成済み）
├── <STIME>/
│   ├── anal/
│   │   ├── 0001/ … 0020/   init_<STIME>.pe*.nc   ← rep_asakura の 1/–20/ から取り込み
│   │   ├── mdet/           init_<STIME>.pe*.nc   ← rep_asakura の 21/ から取り込み
│   │   └── mean/           init_<STIME>.pe*.nc   ← rep_asakura の 21/ から取り込み（mdet と同じ）
│   └── log/scale_init/<member>/
├── <STIME+1h>/ gues/ hist/ anal/ log/ …          ← cycle が書く
├── …
└── obs/

letkf_control/scale/tmp/convection/               ← cycle_run.sh が毎回作り直す作業領域（TMPSUBDIR）
```

## 作成物の分類（もとの 4 節）

| 対象 | 分類 | 内容 |
| --- | --- | --- |
| `cycle_run.sh`, `fcst_run.sh`, `src/`, `config.rc` | `run/` から複製 | 中身は変更しない。例外: `cycle_run.sh` の rscgrp の 1 行を `${RSCGRP:-regular-o}` にした（Phase 3）。`config.rc` の `SCRP_DIR` を `$DIR/run` から `$DIR/convection` にした（Phase 5。これがないと run/ の設定が使われる）。`src/cycle.sh` 468 行の `$atime` を `$time` にした（Phase 6。最初の cycle で LETKC が止まる不具合の修正）。`src/cycle.sh` の step 4 の準備に、LETKC の直前に mdet を `gues/mdet/` にコピーする処理を加えた（Phase 6。制御前の mdet を残す）。`src/cycle.sh` 504 行の `nobs` のコピー先の `$atime` を `$time` にした（Phase 6。`NOBS_OUT=1` で LETKC が止まる不具合の修正） |
| `config.main.Wisteria` | 新規 | OUTDIR, OBSIN, SOUNDING, MEMBER=20, SCALE_NP_X=12, SCALE_NP_Y=12, PPN=4, THREADS=12, TMPSUBDIR=convection |
| `config.cycle`, `config.fcst` | 新規 | STIME, ETIME（24 cycle。2026-10-28 に 48 時間から変更）, TIME_LIMIT, OUT_OPT |
| `config.nml.scale`, `config.nml.scale_init` | 新規 | rep_asakura の `run.conf` / `init.conf_base` に、case_tc テンプレートの `!--XXX--` マーカーを埋め込む |
| `config.nml.letkc`, `config.nml.letkf`, `config.nml.obsmake`, `config.nml.ensmodel`, `config.obsmake` | case_tc から複製して変更 | 格子・分割数・メンバー数に依存する項目のみ |
| `init/*` | 新規 | 1.3 節のとおり |
| `dat/*` | rep_asakura からコピー | |
| `make_obsin/`（controltarget, OBSIN） | 作り直し | case_tc 格子（25 km, 8 × 4）用なので流用不可。controltarget は `make_obsin/controltarget/make_controltarget.py`、OBSIN は `make_obsin/obsin/make_obsin.py`（Phase 7） |
| 実行ファイル（`scale-rm_*_ens`, `letkc`, `letkf`, `obsmake`, `obsope`） | そのまま使う | letkf_control でビルド済みのもの |

case_tc の namelist は物理設定が大きく異なる（25 km, KMAX = 20, 陸面・放射なし, SF = BULK）。
そのため `config.nml.scale*` は case_tc から「コピーして一部変更」ではなく、
rep_asakura の物理設定を元に作る。

## Phase 2 の手順（もとの 5 節）

```bash
cd /work/02/gv42/v42013/scale-letkc/letkf_control/scale
cp -p run/cycle_run.sh run/fcst_run.sh run/config.rc convection/
cp -rp run/src convection/
mkdir -p convection/init convection/dat convection/make_obsin
R=../../scale-rm/test/case/rep_asakura
cp -rp $R/PARAG.29 $R/PARAPC.29 $R/VARDATA.RM29 $R/cira.nc $R/MIPAS $R/param.bucket.conf convection/dat/
cp -rp $R/ensperturb convection/init/
cp -p $R/init.conf_base $R/init.sh_base convection/init/
```

### 完了条件

`convection/` に 1.2 節の構成（設定ファイルの中身は未作成）がそろっている。
