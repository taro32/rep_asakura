# Phase 0 — 現状保存と実験条件の確定：計画書から移した詳細

準備の計画書（`../20260923_experiment_plan.md`）を簡潔にしたとき（2026-11-06）に、そこから移した詳細。中身は書いた当時のまま。
パスはフォルダの整理（2026-11-06）の前のもの（`init/` → `setup/init/` など。対応は `convection/README.md`）。節の番号は、もとの計画書のもの。

## 経緯（もとの改訂履歴から）

- 2026-09-23: 実験ディレクトリを `letkf_control/scale/convection/` に一本化
- 2026-09-24: 実験規模を **2 km × 20 member** に変更（4 km 案を取りやめ）
- 2026-09-25: Phase 0–5 完了
  - Phase 0: STIME = 20000101000000、ETIME = 20000103000000（スピンアップなし）、OUTDIR を確定

## 進捗のチェックリスト（もとの「進捗状況」から）

- [x] Phase 0 — 現状保存と実験条件の確定 — 2026-09-25
  - [x] 0-1 git の状態を固める（.gitignore、staged ファイルの整理、タグ） — 2026-09-25
  - [x] 0-2 構成と実行ファイルの記録（`docs/phase0/`） — 2026-09-25
  - [x] 0-3 既存 2 km 生成物の保全（読み取り専用化、`1/`–`21/` の md5） — 2026-09-25
  - [x] 0-4 STIME とスピンアップの確認 — 2026-09-25
  - [x] 0-5 OUTDIR とノード時間予算の確定 — 2026-09-25

## もとの計画書の目的

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
1 cycle → 2 cycle → 24 時間
```

## 配置方針（もとの 1.1 節）

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

## 実験規模・資源・予算（もとの 1.4 節）

先生の助言（メンバー数を減らす）を受け、格子は既存 rep_asakura の 2 km を維持し、メンバー数だけを減らす。

| 項目 | 既存 rep_asakura | convection | 備考 |
| --- | --- | --- | --- |
| 水平格子 | 2 km | **2 km** | 変更しない |
| 領域 | 120 × 120 格子 = 240 km 四方（周期） | 同じ | |
| MPI 分割 | 12 × 12（IMAX = JMAX = 10） | **12 × 12** | 1 member = 144 プロセス = 36 ノード |
| 鉛直 | KMAX = 64 | 同じ | |
| 時間ステップ | `TIME_DT=6s`, `TIME_DT_ATMOS_DYN=3s` | 同じ | |
| アンサンブル | 101 | **20 + mdet** | |
| cycle 期間 | — | **24 時間**（LCYCLE = 3600 s で 24 cycle） | `STIME = 20000131000000`（Phase 7d、30 日スピンアップ後）。2026-10-28 に 48 時間から変更（§1） |
| 必要ノード数 | — | (20 + 2) × 36 = **792 ノード** | `DET_RUN=1`, `PPN=4`, `THREADS=12` |
| rscgrp | — | `regular-o` で投げ、80 member・1,476 ノードは **x-large-o**（最大 2,304 ノード・24 時間）に振り分けられる | 20 member（792 ノード）なら large-o（2026-10-28 に更新） |

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
- 1 member × 1 時間の予報は 21 秒（Phase 3 で実測）。80 member・10 km の 24 cycle は 3:56（感度実験 M80L10_24）なので、
  **24 cycle を 1 ジョブで流す**（2026-10-28 に更新。`TIME_LIMIT` は x-large-o の上限 24 時間以内で、余裕を見て決める）。
- 動作確認（`MEMBER=2`）は debug-o で行う。`config.main.Wisteria` の `RSCGRP` で切り替える（Phase 3 の決定）。
- 計算量は 4 km 案の約 8 倍（水平格子数 4 倍 × 時間ステップ数 2 倍）。

### 予算とディスク（2026-09-25 に `show_token`・`show_quota` で確認）

| 項目 | 状況 | 本実験の見込み |
| --- | --- | --- |
| ノード時間（gv42 グループ） | 上限 648,000、使用 453,416（69%）、残り約 195,000。期限 2027-03-31 | 80 member・10 km の 24 cycle は 1,476 ノード × 3:56 で約 5,800（感度実験 M80L10_24 の実績、2026-10-28 に更新） |
| ディスク（`/work/gv42` グループ全体） | 上限約 301 TB、使用約 294 TB、**残り約 6.7 TB** | restart だけで 1 cycle あたり約 23 GB（82 個 × gues/anal × 143 MB）、24 cycle で約 0.6 TB。member の history も残すと 20 member で 1 cycle 約 30 GB だったので、80 member の 24 cycle で約 3 TB（2026-10-28 に更新） |

- ノード時間の見込みは Phase 3 で 1 cycle の実行時間を測ってから確定する。
- グループ全体のディスクの空きが少ないので、history の出力変数・間隔は必要なものに絞る。

## Phase 0 の手順と決定（もとの 5 節）

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
- 本番は 24 cycle とする（2026-10-28 に 48 時間から変更。§1）。

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

## テスト戦略（もとの 6 節）

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
| 9 | 24 時間 | MEMBER=80, 1,476 ノード（member を 2 回に分ける） | 8 |

## 変更しないもの（もとの 7 節）

```text
letkf_control/scale/run/ 以下（case_tc の設定・シンボリックリンク・src/）
scale-rm/test/case/rep_asakura/ 以下（2 km テンプレート・生成物・ensperturb）
SCALE-RM 本体、letkf_control の実行ファイル
convection/src/ の cycle 本体（run/src からの複製のまま使う）
```

## 完成条件（もとの 9 節）

第一段階: M1（Phase 6）。

最終的には、次の cycle を convection/ の設定で 24 時間実行できる状態にする。

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
