# convection — rep_asakura 設定での EnKC cycle 実験 作業計画

改訂履歴:
- 2026-09-23: 実験ディレクトリを `letkf_control/scale/convection/` に一本化
- 2026-09-24: 実験規模を **2 km × 20 member** に変更（4 km 案を取りやめ）
- 2026-09-25: Phase 0–5 完了
  - Phase 0: STIME = 20000101000000、ETIME = 20000103000000（スピンアップなし）、OUTDIR を確定
  - Phase 1: case_tc の依存関係を調査（`docs/phase1/dependency.md`）。静的入力は `convection/dat/` にコピーする
  - Phase 3: 1 member × 1 時間の予報が 21 秒と判明。48 cycle を 1 ジョブ・`TIME_LIMIT = 12:00:00` で流す。
    debug-o を `config.main.Wisteria` の `RSCGRP` で切り替えられるようにした（`cycle_run.sh`）
  - Phase 4: 初期値の取り込みで、STIME の mean にも mdet（rep_asakura の `21/`）をコピーする
  - Phase 5: history は rep_asakura の 108 項目に同化で必要な 5 項目を加えた 113 項目、10 分ごと（`FCSTOUT = 600`）。
    `config.rc` の `SCRP_DIR` を `$DIR/convection` にした（`run/` の設定が使われる不具合の修正）。MEMBER = 20 で step 1–3 を確認
- 2026-09-26: Phase 6（M1）の方針と M1a
  - M1 は制御なし（地上気圧 10 hPa の controltarget）で通し、その後に制御の中身を変える。
    M1a（配管）と M1b（制御の本体）の 2 段階に分けた。対流性降雨の制御指標の候補を 8.1 節に整理
  - `src/cycle.sh` の不具合（最初の cycle で LETKC が止まる。case_tc でも起きていた）を修正し、M1a に合格。
    M1a の合格条件を「LETKC 後の mdet の初期値が元の値と丸め誤差の範囲で一致」に改めた
  - LETKC の直前に制御前の mdet を `gues/mdet/` に取っておくようにした（`src/cycle.sh`）
  - M1b の controltarget: 地上気圧 1000.03 hPa・誤差 0.01 hPa・高さ 0 m（アンサンブルのばらつきと同程度の大きさ）

## 進捗状況

完了したら `[ ]` を `[x]` にし、行末に完了日を書く（例: `— 2026-09-25`）。

- [x] Phase 0 — 現状保存と実験条件の確定 — 2026-09-25
  - [x] 0-1 git の状態を固める（.gitignore、staged ファイルの整理、タグ） — 2026-09-25
  - [x] 0-2 構成と実行ファイルの記録（`docs/phase0/`） — 2026-09-25
  - [x] 0-3 既存 2 km 生成物の保全（読み取り専用化、`1/`–`21/` の md5） — 2026-09-25
  - [x] 0-4 STIME とスピンアップの確認 — 2026-09-25
  - [x] 0-5 OUTDIR とノード時間予算の確定 — 2026-09-25
- [x] Phase 1 — case_tc の依存関係の確定 — 2026-09-25
  - [x] スクリプト → 実行ファイル → 設定の対応表 — 2026-09-25（`docs/phase1/dependency.md`）
  - [x] `scale-rm_init_ens`（step 2, 6）が陸面状態を上書きしないか — 2026-09-25（上書きしない。step 2・6 は飛ばされる）
  - [x] LETKC / LETKF での陸面変数の扱い — 2026-09-25（触らない。大気 11 変数だけ）
  - [x] controltarget の入力形式 — 2026-09-25
- [x] Phase 2 — convection/ の骨組み作成（framework・dat・init のコピー） — 2026-09-25
- [x] Phase 3 — 単独 forecast と実行時間の計測 — 2026-09-25
  - [x] 1 member × 1 時間の実行時間 — 2026-09-25（21 秒。`docs/phase3/fcst1h_result.md`）
  - [x] 1 cycle の所要時間の見積もりと `TIME_LIMIT`・ジョブ分割の方針 — 2026-09-25（数分／cycle。1 ジョブ・TIME_LIMIT 12 時間。debug-o を切り替え可能に）
- [x] Phase 4 — 初期値を OUTDIR に取り込む（md5 一致を確認） — 2026-09-25（22 member、`docs/phase4/import_result.md`）
- [x] Phase 5 — cycle 設定の作成と ensemble forecast の接続 — 2026-09-25
  - [x] `config.main.Wisteria`, `config.cycle`, `config.nml.*` の作成 — 2026-09-25（`docs/phase5/config_notes.md`）
  - [x] step 1–3（MEMBER=2） — 2026-09-25（16 秒。0001 は Phase 3 と完全一致。`docs/phase5/config_notes.md`）
  - [x] step 1–3（MEMBER=20） — 2026-09-25（large-o、25 秒。22 本すべて正常）
- [ ] Phase 6 — LETKC と mdet controlled forecast（**M1**）
  - [x] 2 km 格子のダミー controltarget — 2026-09-26（制御なし 10 hPa。`make_obsin/controltarget/make_controltarget.py`）
  - [x] M1a（配管）: 制御なしで step 1–7 正常終了、LETKC 後の mdet の初期値が元と丸め誤差の範囲で一致 — 2026-09-26（2 回目で合格。`docs/phase6/m1_notes.md`）
  - [ ] M1b（制御の本体）: 受け入れられる目標で、mdet の最下層の水蒸気が目標のまわりだけ減る
- [ ] Phase 7 — obsmake / OBSOPE / LETKF
  - [ ] 2 km 格子用の OBSIN
  - [ ] step 1–10 正常終了（0001–0020 の analysis）
- [ ] Phase 8 — cycling
  - [ ] 1 cycle
  - [ ] 2 cycle（時刻・restart の引き継ぎの整合）
  - [ ] 48 時間


## 0. 目的

現在正常に動作している `case_tc` の EnKC（LETKC）cycling 実装を使い、
`rep_asakura` の理想化実験（2 km・全陸面・二重周期・BUCKET陸面・放射あり）の設定で
**EnKC を含む cycle を実行できる状態にすること**を目的とする。

この段階では EnKC のアルゴリズムや cycling 構造を新しく設計しない。

```text
既存の case_tc EnKC 実装（letkf_control/scale/run）
        ↓
依存関係を確認
        ↓
letkf_control/scale/convection/ に run/ の framework を複製
        ↓
rep_asakura の初期値・物理設定（2 km のまま）を convection/ に持ち込む
        ↓
初期値を OUTDIR に配置
        ↓
case_tc と同じ経路で EnKC を実行
        ↓
1 cycle → 2 cycle → 48 時間
```

---

# 1. 決定事項

## 1.1 配置方針（2026-09-23 決定）

新しい実験に必要なスクリプト・設定・入力は、すべて
`letkf_control/scale/convection/` に置く。計算結果はすべて `$OUTDIR` に置く。

| 役割 | 置き場所 | 備考 |
| --- | --- | --- |
| cycle framework（`cycle_run.sh`, `fcst_run.sh`, `src/`, `config.rc`） | `convection/` | `run/` から複製する |
| cycle 設定（`config.main.Wisteria`, `config.cycle`, `config.nml.*`） | `convection/` | rep_asakura の物理設定（2 km）から作る |
| 初期アンサンブル生成（スクリプト・テンプレート・摂動サウンディング） | `convection/init/` | rep_asakura の処理を元に作る |
| 放射・陸面の静的入力 | `convection/dat/` | rep_asakura からコピー |
| controltarget・観測入力の作成 | `convection/make_obsin/` | case_tc の `make_obsin/` を元に 2 km 格子用に作り直す |
| 計画書・記録 | `convection/docs/` | |
| **計算結果（初期値を含むすべてのデータ）** | **`$OUTDIR` の1か所** | 初期値も cycle の結果も同じ `$OUTDIR` に置く |
| 既存 `run/`（case_tc） | 変更しない | シンボリックリンクも切り替えない |
| 既存 `scale-rm/test/case/rep_asakura/`（2 km・101 member） | 変更しない | 初期値の取り込み元・過去実験として残す |

`convection/` は `run/`・`run_10/`・`run_light/` と同じ階層にある。
`cycle_run.sh` は `DIR=$(pwd)/..`、`SCALEDIR=$DIR/../..` でパスを決めるので、
`convection/` から実行しても `DIR=letkf_control/scale` となり、
実行ファイル（`ensmodel/`, `letkc/`, `letkf/`, `obs/`）の参照は `run/` と同じになる。

## 1.2 ディレクトリ構成

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
└── docs/                                     ← 本書・Phase 0 の記録

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

## 1.3 初期値と cycle のつなぎ方

- cycle は `MAKEINIT=0` で `$INDIR/$STIME/anal/<member>/init_*.nc` を読む
  （`src/func_cycle_static.sh` の `RESTART_IN_PATH`）。`INDIR=$OUTDIR` とする。
- **2 km のままなので、rep_asakura で作成済みの初期値をそのまま使える。**
  `init/import_rep_asakura.sh` で次のように `$OUTDIR/$STIME/anal/` にコピーする。

  | rep_asakura | OUTDIR | 摂動サウンディング |
  | --- | --- | --- |
  | `1/` – `20/` | `anal/0001/` – `anal/0020/` | env_perturb1–20 |
  | `21/` | `anal/mdet/` | env_perturb21 |
  | `21/` | `anal/mean/` | env_perturb21（Phase 4 で追加。case_tc と同じく STIME の mean は mdet のコピー） |

  1 member あたり約 143 MB（144 プロセス分の `init_20000101-000000.000.pe*.nc`）で、合計約 3 GB。
- 取り込み後、cycle が読むのは `$OUTDIR` だけとする（rep_asakura を直接参照しない）。
- 初期値テンプレートには `RANDOM_THETA=0.1` があり、作り直すと既存の初期値とは別のアンサンブルになる可能性がある。
  そのため既存の初期値を優先して使い、`init/ensinit.sh`（OUTDIR に直接出力する版）は
  STIME を変える場合（スピンアップ後に開始する場合など）の再生成用とする。
- `init/` のスクリプトは `../config.main` と `../config.cycle` を読み込み、
  `OUTDIR`・`STIME`・`MEMBER` を cycle と共通の値で使う（設定の二重管理をしない）。
- メンバー対応（`1–20 → 0001–0020`、`21 → mdet`）は `init/` のスクリプトの1か所だけで定義する。

## 1.4 実験規模（2026-09-24 決定）

先生の助言（メンバー数を減らす）を受け、格子は既存 rep_asakura の 2 km を維持し、メンバー数だけを減らす。

| 項目 | 既存 rep_asakura | convection | 備考 |
| --- | --- | --- | --- |
| 水平格子 | 2 km | **2 km** | 変更しない |
| 領域 | 120 × 120 格子 = 240 km 四方（周期） | 同じ | |
| MPI 分割 | 12 × 12（IMAX = JMAX = 10） | **12 × 12** | 1 member = 144 プロセス = 36 ノード |
| 鉛直 | KMAX = 64 | 同じ | |
| 時間ステップ | `TIME_DT=6s`, `TIME_DT_ATMOS_DYN=3s` | 同じ | |
| アンサンブル | 101 | **20 + mdet** | |
| cycle 期間 | — | **48 時間**（LCYCLE = 3600 s で 48 cycle） | `STIME = 20000101000000`, `ETIME = 20000103000000`（2026-09-25 決定、スピンアップなし） |
| 必要ノード数 | — | (20 + 2) × 36 = **792 ノード** | `DET_RUN=1`, `PPN=4`, `THREADS=12` |
| rscgrp | — | **large-o**（577–1152 ノード、最大 48 時間） | |

### 資源の上限（Wisteria-O、`pjstat --rsc -x` で 2026-09-24 に確認）

| rscgrp | 最大ノード | 最大経過時間 | 2 km で入る member 数 |
| --- | --- | --- | --- |
| debug-o / small-o | 144 | 0.5 h / 48 h | 2 |
| medium-o | 576 | 48 h | 14 |
| large-o | 1152 | 48 h | 30 |
| x-large-o | 2304 | 24 h | 62 |

- 100 member（3672 ノード）はどの rscgrp にも入らない。
- 20 member は large-o に収まる。将来 member を増やす場合、large-o のままなら 30 が上限。
- 動作確認は `MEMBER=2`（(2 + 2) × 36 = 144 ノード）にすれば debug-o / small-o で実行できる。
- 1 member × 1 時間の予報は 21 秒（Phase 3 で実測）。1 cycle は数分、48 cycle は数時間の見込みなので、
  **48 cycle を 1 ジョブで流し、`TIME_LIMIT = 12:00:00` とする**（2026-09-25 決定）。
- 動作確認（`MEMBER=2`）は debug-o で行う。`config.main.Wisteria` の `RSCGRP` で切り替える（Phase 3 の決定）。
- 計算量は 4 km 案の約 8 倍（水平格子数 4 倍 × 時間ステップ数 2 倍）。

### 予算とディスク（2026-09-25 に `show_token`・`show_quota` で確認）

| 項目 | 状況 | 本実験の見込み |
| --- | --- | --- |
| ノード時間（gv42 グループ） | 上限 648,000、使用 453,416（69%）、残り約 195,000。期限 2027-03-31 | 792 ノード × 48 cycle × 1 cycle の時間。1 cycle = 30 分なら約 19,000（残りの約 10%）、1 時間なら約 38,000（約 20%） |
| ディスク（`/work/gv42` グループ全体） | 上限約 301 TB、使用約 294 TB、**残り約 6.7 TB** | restart だけで 1 cycle あたり約 6 GB（22 member × gues/anal × 143 MB）、48 cycle で約 300 GB。history の量は Phase 3 で確認する |

- ノード時間の見込みは Phase 3 で 1 cycle の実行時間を測ってから確定する。
- グループ全体のディスクの空きが少ないので、history の出力変数・間隔は必要なものに絞る。

---

# 2. 移植元の構造

## 2.1 case_tc（cycle framework）

| パス | 性質 |
| --- | --- |
| `letkf_control/scale/run/src/` | cycle スクリプト本体（**複製元**） |
| `letkf_control/scale/run/config/case_tc/` | case_tc のケース設定（**参考**。namelist の `!--XXX--` マーカーの位置を引き継ぐ） |
| `letkf_control/scale/tmp/<TMPSUBDIR>/` | `cycle_run.sh` が実行ごとに作り直す作業領域。**移植元ではない** |

### step とは

1 回の cycle（時刻 t → t+1h）は、決まった順番の処理でできている。
cycle スクリプトはこの処理に 1〜11 の番号を付けていて、これを **step** と呼ぶ
（定義は `src/func_cycle_static.sh`、`DET_RUN_UPDATE=2` のとき）。
`cycle_run.sh` の引数 `ISTEP`・`FSTEP` で、何番の step から何番の step までを実行するかを指定できる。

| step | 実行ファイル | やること | convection での扱い |
| --- | --- | --- | --- |
| 1 | `scale-rm_pp_ens` | 地形・土地利用のファイルを作る | **飛ばす**（地形なし・全面陸） |
| 2 | `scale-rm_init_ens` | 初期値をゼロから作る | **飛ばす**（`BDY_FORMAT=5`。初期値は Phase 4 で用意） |
| **3** | `scale-rm_ens` | **全 member（0001〜0020・mean・mdet）の 1 時間予報** | 実行する |
| **4** | `letkc` | **LETKC**: step 3 の予報と controltarget から、mdet の初期値を修正する（制御） | 実行する |
| 5 | `scale-rm_pp_ens` | step 1 と同じ | 飛ばす |
| 6 | `scale-rm_init_ens` | step 2 と同じ | 飛ばす |
| **7** | `scale-rm_ens` | **修正後の mdet を含めて、1 時間予報をやり直す**（全 member） | 実行する |
| **8** | `obsmake` | **mdet の予報から観測を作る** | 実行する |
| 9 | `obsope` | 観測演算子を単独で計算する | 飛ばす（step 10 の中で計算する） |
| **10** | `letkf` | **LETKF**: 観測を使って 0001〜0020 の解析値を作る。これが次の cycle の初期値になる | 実行する |
| 11 | `efso` | 観測の影響評価 | 飛ばす（`EFSO_RUN=0`） |

入出力のファイルなど詳しいことは `docs/phase1/dependency.md` の 2 節にある。

この構造は変更しない。

## 2.2 rep_asakura（物理設定・初期値）

| rep_asakura のファイル | convection での扱い |
| --- | --- |
| `1/` – `21/` の `init_20000101-000000.000.pe*.nc` | `$OUTDIR/<STIME>/anal/{0001..0020,mdet}/` に取り込む |
| `init.conf_base` | `init/init.conf_base`（再生成用）と `config.nml.scale_init` の元にする。格子・分割は変えない |
| `run.conf` | `config.nml.scale` の元にする。`!--XXX--` マーカーを入れ、静的入力を `convection/dat/` の絶対パスにする |
| `ensinit.sh`, `init.sh_base` | `init/` に OUTDIR 直接出力版として作る（再生成用） |
| `ensperturb/`（env.txt, env_perturb1–21, sounding_perturb.py） | `init/ensperturb/` にコピー（乱数を振り直さない） |
| 静的入力（PARAG.29 など） | `dat/` にコピー |
| `preprocess_init.sh`, `letkfinput/` | 使わない |

---

# 3. member の扱い

```text
0001–0020 : ensemble（LETKC の guess、LETKF の ensemble）
mdet       : deterministic / control（21番目の member として扱わない）
```

---

# 4. 作成物の分類

| 対象 | 分類 | 内容 |
| --- | --- | --- |
| `cycle_run.sh`, `fcst_run.sh`, `src/`, `config.rc` | `run/` から複製 | 中身は変更しない。例外: `cycle_run.sh` の rscgrp の 1 行を `${RSCGRP:-regular-o}` にした（Phase 3）。`config.rc` の `SCRP_DIR` を `$DIR/run` から `$DIR/convection` にした（Phase 5。これがないと run/ の設定が使われる）。`src/cycle.sh` 468 行の `$atime` を `$time` にした（Phase 6。最初の cycle で LETKC が止まる不具合の修正）。`src/cycle.sh` の step 4 の準備に、LETKC の直前に mdet を `gues/mdet/` にコピーする処理を加えた（Phase 6。制御前の mdet を残す） |
| `config.main.Wisteria` | 新規 | OUTDIR, OBSIN, SOUNDING, MEMBER=20, SCALE_NP_X=12, SCALE_NP_Y=12, PPN=4, THREADS=12, TMPSUBDIR=convection |
| `config.cycle`, `config.fcst` | 新規 | STIME, ETIME（STIME + 48h）, TIME_LIMIT, OUT_OPT |
| `config.nml.scale`, `config.nml.scale_init` | 新規 | rep_asakura の `run.conf` / `init.conf_base` に、case_tc テンプレートの `!--XXX--` マーカーを埋め込む |
| `config.nml.letkc`, `config.nml.letkf`, `config.nml.obsmake`, `config.nml.ensmodel`, `config.obsmake` | case_tc から複製して変更 | 格子・分割数・メンバー数に依存する項目のみ |
| `init/*` | 新規 | 1.3 節のとおり |
| `dat/*` | rep_asakura からコピー | |
| `make_obsin/`（controltarget, OBSIN） | 作り直し | case_tc 格子（25 km, 8 × 4）用なので流用不可。M1 用には 2 km 格子のダミーを作る |
| 実行ファイル（`scale-rm_*_ens`, `letkc`, `letkf`, `obsmake`, `obsope`） | そのまま使う | letkf_control でビルド済みのもの |

case_tc の namelist は物理設定が大きく異なる（25 km, KMAX = 20, 陸面・放射なし, SF = BULK）。
そのため `config.nml.scale*` は case_tc から「コピーして一部変更」ではなく、
rep_asakura の物理設定を元に作る。

---

# 5. 実装フェーズ

## Phase 0 — 現状保存と実験条件の確定

### 0-1. git の状態を固める

- rep_asakura の未コミット変更（`ensinit.sh`、`WORKFLOW.md` → `docs/`）を確認してコミットする。
- rep_asakura の member ディレクトリ・`letkfinput/`・NetCDF・LOG を `.gitignore` に追加する。
- letkf_control 側で staged になっている実行ファイル・NetCDF（`letkc`, `efso`, `scale-rm_*_ens`,
  `merged_history1.pe000000.nc` など）をコミットに含めるかを判断する（含めない場合は `git restore --staged`）。
- タグを付ける: `rep_asakura_2km`、`case_tc_enkc_working`。

### 0-2. 現在の構成と実行ファイルの記録（`convection/docs/phase0/`）

```bash
cd /work/02/gv42/v42013/scale-letkc
mkdir -p letkf_control/scale/convection/docs/phase0
D=letkf_control/scale/convection/docs/phase0
( cd scale-rm/test/case/rep_asakura && md5sum *.sh *.conf *_base ensperturb/* ) > $D/rep_asakura_scripts.md5
ls -lL bin/scale-rm bin/scale-rm_init \
       letkf_control/scale/ensmodel/scale-rm_*_ens \
       letkf_control/scale/letkc/letkc > $D/executables.txt
md5sum bin/scale-rm bin/scale-rm_init >> $D/executables.txt
```

`bin/scale-rm`・`bin/scale-rm_init` は letkf_control 側の再ビルドで中身が変わりうるので、md5 を記録しておく。

### 0-3. 既存 2 km 生成物の保全

- rep_asakura の `1/`–`101/` と `letkfinput/` はそのまま残し、読み取り専用にする（`chmod -R a-w`）。
  特に `1/`–`21/` は本実験の初期値の取り込み元になる。
- 取り込み元の初期値の md5 を記録する:
  ```bash
  cd scale-rm/test/case/rep_asakura
  for m in $(seq 1 21); do md5sum $m/init_20000101-000000.000.pe*.nc; done > $D/init_1-21.md5
  ```
- `ensperturb/env_perturb*.txt` がコミット済みであることを確認する（乱数シードは固定されていない）。

### 0-4. 開始時刻（STIME）とスピンアップの確認

- rep_asakura の `run.conf` は `./init_per_SM_R131_0.1_1/perturbed_restart_20000131-000000.000` を読んでいるが、
  このディレクトリは rep_asakura に存在しない。
- 20000131 の restart（30日スピンアップ＋土壌水分摂動と推定）の作成手順と所在を確認する。
- 次のどちらかを決める。
  - (a) スピンアップ後の時刻を STIME とする。スピンアップ済みの restart が 21 member 分あればそれを取り込む。
    なければ 21 member × 30 日のスピンアップが必要になる（2 km のため計算量が大きい）。
  - (b) 20000101 の既存初期値から直接 cycle を始める（`STIME=20000101000000`）。
- `ETIME = STIME + 48h` とする。

**決定（2026-09-25）: (b) を採用する。** `STIME = 20000101000000`、`ETIME = 20000103000000`。

- 20000131 の restart（`init_per_SM_R131_0.1_1/`）は `/work/02/gv42/v42013` の下に見つからなかった。
- そのため、スピンアップせずに rep_asakura の既存初期値（`1/`–`21/`）から cycle を始める。
- 土壌水分はスピンアップなしの初期値のまま始まる。control target の検討（8 節）ではこのことを前提にする。

### 0-5. 実験条件の確定

- `OUTDIR` のパスを決める。
- ノード時間の予算を確認する（792 ノード × cycle 実行時間）。
- 確定値は本書の 1.4 節を更新して記録する。

**決定（2026-09-25）:** `OUTDIR = /work/gv42/v42013/20260923_enkc_convection/result`（作成済み）。
予算とディスクの状況は 1.4 節の「予算とディスク」に記録した。

### 完了条件

- 既存の rep_asakura（2 km, 101 member）と case_tc がタグと記録から再現できる。
- STIME / ETIME / OUTDIR が決まっている。

---

## Phase 1 — case_tc の依存関係の確定

```bash
cd letkf_control/scale/run
grep -n "DET_RUN_UPDATE" src/*.sh
grep -n "LETKC_DIR\|OBSUTIL_DIR\|ENSMODEL_DIR\|LETKF_DIR" src/*.sh config.rc
grep -n "stepexecbin\|stepexecname" src/*.sh
grep -n "controltarget\|mdet" src/*.sh config/case_tc/config.nml.*
```

特に確認すること:

- 毎 cycle 実行される `scale-rm_init_ens`（step 2, 6）が、`BDY_FORMAT=5` のときに何をしているか。
  MKINIT で陸面状態（土壌水分）を上書きしないか。
- LETKC / LETKF が restart の陸面変数をどう扱うか（更新しない変数がそのまま引き継がれるか）。
- LETKC の controltarget 入力形式（格子・変数・時刻）。
- `cycle_run.sh` が `SCRP_DIR` 以下のどのファイルを TMP にコピーするか（`convection/` に必要なファイルの一覧）。

### 完了条件

「どのスクリプトが、どの実行ファイルを、どの設定で呼ぶか」が表になっている。

---

## Phase 2 — convection/ の骨組み作成

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

---

## Phase 3 — 単独 forecast と実行時間の計測

- `config.nml.scale` と同じ物理設定で、1 member（rep_asakura の `1/` の初期値）を 1 時間積分する（debug-o, 36 ノード）。
- 1 時間積分にかかる実時間を記録し、1 cycle の所要時間を見積もる。
  step 7 は step 3 と同じく全 member の予報をやり直すので、1 cycle は「予報 2 回 + LETKC + obsmake + LETKF」になる（`docs/phase1/dependency.md` 4.4 節）。
- 48 cycle を1ジョブ（large-o, 最大 48 時間）で流せるかを判断し、`TIME_LIMIT` を決める。
- 動作確認に debug-o（最大 144 ノード・30 分）を使うかを決める。
  1 cycle が 30 分に収まるなら、`convection/cycle_run.sh` の `rscgrp=regular-o` を `config.main.Wisteria` から切り替えられるようにする。
  収まらないなら regular-o のまま使う（`docs/phase1/dependency.md` 4.5 節）。

### 結果と決定（2026-09-25）

記録は `docs/phase3/fcst1h_result.md`。

- 1 member × 1 時間の予報は **21 秒**で正常終了した。対流が発生し、値も妥当（図は `docs/phase3/figs/`）。
- 1 cycle は数分、48 cycle は数時間の見込み。
- **ジョブ分割**: 48 cycle を 1 ジョブで流す。**`TIME_LIMIT = 12:00:00`**（`config.cycle` に書く。2 cycle の試験の実績を見て調整する）。
- **rscgrp**: debug-o を使えるようにする。`convection/cycle_run.sh` の `#PJM -L "rscgrp=regular-o"` を
  `#PJM -L "rscgrp=${RSCGRP:-regular-o}"` に変えた（`run/` からの唯一の変更）。
  `config.main.Wisteria` で `RSCGRP=debug-o` とすれば debug-o、書かなければ regular-o になる。
- **単独実行の出力の置き方**: history・refstate・restart を種類ごと・member ごとに分ける
  （例: `$OUTDIR/phase3_fcst1h/history/1/`）。cycle の出力は framework が `<time>/{anal,gues,hist}/<member>/` に分けるので、そちらは変えない。
- **history の量**: 今の設定（60 秒ごと・108 項目）のままだと cycle 全体で約 7 TB になり、ディスクの空きを超える。Phase 5 で絞る。

### 完了条件

1 cycle あたりの所要時間の見積もり、ジョブ分割の方針、動作確認に使う rscgrp が決まっている。

---

## Phase 4 — 初期値を OUTDIR に取り込む

- `init/import_rep_asakura.sh` を作り、1.3 節の対応表どおりに `$OUTDIR/$STIME/anal/{0001..0020,mdet}/` へコピーする。
- コピー後の md5 が Phase 0-3 の記録と一致することを確認する。
- STIME を 20000101 以外にする場合（0-4 の (a)）は、スピンアップ後の restart を同じ形で取り込むか、
  `init/ensinit.sh` で再生成する。

### 完了条件

`$OUTDIR/$STIME/anal/` に 20 + mdet の初期値がそろっている。

---

## Phase 5 — cycle 設定の作成と ensemble forecast の接続

- 4 節の分類に従って `config.main.Wisteria`, `config.cycle`, `config.nml.*` を作る。
- まず `MEMBER=2`（144 ノード, debug-o）で `ISTEP=1`, `FSTEP=3` を実行し、step 1–3 の設定を確認する。
- 次に `MEMBER=20`（792 ノード, large-o）で同じ範囲を実行する。

### 完了条件

`$OUTDIR/<STIME+1h>/gues/` に 0001–0020 と mdet の forecast が出力される。

---

## Phase 6 — LETKC と mdet controlled forecast（M1）

- `make_obsin/` で 2 km 格子（120 × 120）のダミー controltarget を作る。
- `FSTEP=7` まで実行する（MEMBER=20、regular-o）。

### 最初の重要マイルストーン（M1）

```text
0001–0020 → ensemble forecast → LETKC → mdet → mdet controlled forecast
```

が convection/ の設定で正常終了すること。

### M1 を 2 段階に分ける（2026-09-26 決定）

制御なしの試験では、LETKC は最後まで動くが、制御の計算そのもの（重みを計算して mdet を修正する部分）は通らない。
そこで、「LETKC を convection の設定でつなぎ込めたか（配管）」と「制御が正しく効くか（本体）」を分けて確かめる。
先に M1a で配管の問題を切り分けておけば、M1b で何かおかしかったときに、制御の計算の問題に絞り込める。

| 段階 | controltarget | 確かめること | 合格の条件 |
| --- | --- | --- | --- |
| **M1a（配管）** | 地上気圧 **10 hPa**（制御なし。必ず捨てられる） | 20 member の history・restart を 12 × 12 分割・2 km 格子で読めるか。history の必要な変数（Umet, SFC_PRES など）があるか。controltarget を読み、目標地点のモデルの値を計算して捨てる判定が働くか。mdet を書き出して step 7 で読めるか | step 1–7 が異常終了なしで通り、**LETKC で書き直された mdet の初期値が元の値と丸め誤差（1e-12 以下）の範囲で一致する**（当初の「step 7 の mdet が step 3 と完全に一致」は、LETKC が丸め誤差を入れるので満たせないと分かり、2026-09-26 に改めた） |
| **M1b（制御の本体）** | 地上気圧を **必ず受け入れられる値**（目標地点のモデルの気圧より少し高い値。例: +1 hPa） | 重みを計算して mdet の水蒸気を実際に修正するか | mdet の **最下層の水蒸気が、目標地点のまわりだけで減っている**。修正が局所化の範囲（`HORI_LOCAL` × 3.65）の外に出ていない。0001〜0020 は変わっていない。制御前の mdet が `gues/mdet/` に残っている。制御による step 7 の変化が、M1a で分かった雑音（MOMZ 0.04、RHOT 0.09 K 程度）より十分大きい |

- M1b の地上気圧は、指標として選んだものではなく、**コードで動作実績のある要素で制御の実装を確かめるため**に使う。
  対流性降雨の制御指標は M1 の後に決める（8.1 節）。
- 詳しい記録は `docs/phase6/m1_notes.md`。

---

## Phase 7 — obsmake / OBSOPE / LETKF

- `make_obsin/` で 2 km 格子用の `OBSIN` を作る。
- `FSTEP=10` まで実行し、`0001–0020` の analysis が出ることを確認する。

---

## Phase 8 — 1 cycle → 2 cycle → 48 時間

1. `ETIME = STIME + 1h` で 1 cycle 全体。
2. `ETIME = STIME + 2h` で 2 cycle。analysis → 次 cycle の restart、mdet の引き継ぎ、
   観測・controltarget・history・LETKC 入出力の時刻の整合を確認する。
3. `ETIME = STIME + 48h` で本実行。`TIME_LIMIT` は Phase 3 と 2 cycle の実績から設定する
   （必要なら複数ジョブに分割する）。

---

# 6. テスト戦略

| Test | 内容 | 規模 | 対応 Phase |
| --- | --- | --- | --- |
| 1 | 単独 forecast・実行時間計測 | 1 member, 36 ノード | 3 |
| 2 | 初期値の取り込み（md5 一致） | — | 4 |
| 3 | ensemble forecast（step 1–3） | MEMBER=2 → 20 | 5 |
| 4 | LETKC + mdet controlled forecast（**M1**） | MEMBER=2 → 20 | 6 |
| 5 | obsmake | MEMBER=20 | 7 |
| 6 | OBSOPE / LETKF | MEMBER=20 | 7 |
| 7 | 1 cycle | MEMBER=20 | 8 |
| 8 | 2 cycle | MEMBER=20 | 8 |
| 9 | 48 時間 | MEMBER=20, 792 ノード | 8 |

---

# 7. 変更しないもの

```text
letkf_control/scale/run/ 以下（case_tc の設定・シンボリックリンク・src/）
scale-rm/test/case/rep_asakura/ 以下（2 km テンプレート・生成物・ensperturb）
SCALE-RM 本体、letkf_control の実行ファイル
convection/src/ の cycle 本体（run/src からの複製のまま使う）
```

---

# 8. まだ決めないこと（EnKC 移植後に決める）

- 土壌水分を対象とした control target の定義・値・位置・誤差
- 降水観測の配置と観測誤差
- 土壌水分 → 降水の因果関係の評価方法
- 制御あり / なしの比較方法と評価指標
- member 数を増やすかどうか（large-o のままなら 30 が上限）

## 8.1 これまでに分かっていること（2026-09-26）

**進め方:** M1（Phase 6）は **制御なし**（地上気圧 10 hPa の controltarget）で通す。
M1 が通った後に、controltarget と制御の中身を変えていく。

### 今の LETKC の制御の中身（case_tc 向けの作り込み）

- 修正する変数は **最下層の水蒸気（QV）だけ**（`letkc/letkf_tools.f90` 143–146 行、`clev = 1`）。
- **水蒸気を減らす方向の修正しか許していない**（同 649–690 行、`force_check`）。
- 「目標値 − モデルの値」が負の目標は捨てる（`letkc/letkf_obs.f90` 513 行）。
  制御なしは、これを使って満たされない目標（地上気圧 10 hPa）を置くことで作る（`docs/phase1/dependency.md` 3.3 節）。
- 土壌水分で降雨を制御するには、修正する変数の側も変える必要がある。

### 対流性降雨の制御指標の候補

気圧は台風向けの指標で、対流性降雨には向かない（2026-09-26 に議論）。候補と、今のコードで使えるかどうか:

| 候補 | 意味 | 今のコードで使えるか | 注意点 |
| --- | --- | --- | --- |
| 地上降水量（地点・領域の 1 時間積算など） | 最も直接的 | 使えない。雨の観測演算子は未完成でコメントアウトされている（`common_letkc/common_obs_scale.f90`）。history に PREC はあるので追加は比較的容易 | 多くの member で 0 になり、分布が正規分布から大きく外れる。領域平均にすると多少ましになる |
| レーダー反射強度（下層の dBZ） | 降水の強さの代わり。観測として現実的 | 使える（SCALE-LETKF に演算子がある） | 非線形性が強い。降水のない所では値が一定 |
| 下層の水蒸気・相対湿度 | 対流の「燃料」。降雨の前段階 | 使える（`id_q_obs`, `id_rh_obs`） | 降雨そのものではない。LETKC が修正する最下層の QV と直接つながる |
| 上昇流・CAPE など | 対流の強さ・起こりやすさ | 演算子がない | 追加の実装が必要 |

---

# 9. 完成条件

第一段階: M1（Phase 6）。

最終的には、次の cycle を convection/ の設定で 48 時間実行できる状態にする。

```text
                    cycle n
                       │
             ┌─────────┴─────────┐
             │                   │
         0001–0020              mdet
             │                   │
          forecast               │
             └───────┐           │
                     ↓           │
                   LETKC         │
                     ↓           │
                    mdet ←───────┘
                     │
              controlled forecast
                     ↓
                  obsmake
                     ↓
                   OBSOPE
                     ↓
                   LETKF
                     ↓
              0001–0020 analysis
                     ↓
                  cycle n+1
```
