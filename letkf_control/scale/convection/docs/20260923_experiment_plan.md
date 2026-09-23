# convection — rep_asakura 設定での EnKC cycle 実験 作業計画

改訂履歴:
- 2026-09-23: 実験ディレクトリを `letkf_control/scale/convection/` に一本化
- 2026-09-24: 実験規模を **2 km × 20 member** に変更（4 km 案を取りやめ）

## 進捗状況

完了したら `[ ]` を `[x]` にし、行末に完了日を書く（例: `— 2026-09-25`）。

- [ ] Phase 0 — 現状保存と実験条件の確定
  - [ ] 0-1 git の状態を固める（.gitignore、staged ファイルの整理、タグ）
  - [ ] 0-2 構成と実行ファイルの記録（`docs/phase0/`）
  - [ ] 0-3 既存 2 km 生成物の保全（読み取り専用化、`1/`–`21/` の md5）
  - [ ] 0-4 STIME とスピンアップの確認
  - [ ] 0-5 OUTDIR とノード時間予算の確定
- [ ] Phase 1 — case_tc の依存関係の確定
  - [ ] スクリプト → 実行ファイル → 設定の対応表
  - [ ] `scale-rm_init_ens`（step 2, 6）が陸面状態を上書きしないか
  - [ ] LETKC / LETKF での陸面変数の扱い
  - [ ] controltarget の入力形式
- [ ] Phase 2 — convection/ の骨組み作成（framework・dat・init のコピー）
- [ ] Phase 3 — 単独 forecast と実行時間の計測
  - [ ] 1 member × 1 時間の実行時間
  - [ ] 1 cycle の所要時間の見積もりと `TIME_LIMIT`・ジョブ分割の方針
- [ ] Phase 4 — 初期値を OUTDIR に取り込む（md5 一致を確認）
- [ ] Phase 5 — cycle 設定の作成と ensemble forecast の接続
  - [ ] `config.main.Wisteria`, `config.cycle`, `config.nml.*` の作成
  - [ ] step 1–3（MEMBER=2）
  - [ ] step 1–3（MEMBER=20）
- [ ] Phase 6 — LETKC と mdet controlled forecast（**M1**）
  - [ ] 2 km 格子のダミー controltarget
  - [ ] step 1–7 正常終了
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

$OUTDIR  （仮: /work/gv42/v42013/20260923_enkc_convection/result）
├── <STIME>/
│   ├── anal/
│   │   ├── 0001/ … 0020/   init_<STIME>.pe*.nc   ← rep_asakura の 1/–20/ から取り込み
│   │   └── mdet/           init_<STIME>.pe*.nc   ← rep_asakura の 21/ から取り込み
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
| cycle 期間 | — | **48 時間**（LCYCLE = 3600 s で 48 cycle） | `ETIME = STIME + 48h`（STIME は未定） |
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
- 1 cycle の実行時間の実績はまだない（rep_asakura の `LOG.pe000000` は1ステップ目で止まっている）。
  `TIME_LIMIT` と、48 cycle を1ジョブで流せるかどうかは Phase 3 の計測で決める。
  48 時間に収まらない場合は、STIME / ETIME を区切って複数ジョブに分ける。
- 計算量は 4 km 案の約 8 倍（水平格子数 4 倍 × 時間ステップ数 2 倍）。ノード時間の予算を確認する。

---

# 2. 移植元の構造

## 2.1 case_tc（cycle framework）

| パス | 性質 |
| --- | --- |
| `letkf_control/scale/run/src/` | cycle スクリプト本体（**複製元**） |
| `letkf_control/scale/run/config/case_tc/` | case_tc のケース設定（**参考**。namelist の `!--XXX--` マーカーの位置を引き継ぐ） |
| `letkf_control/scale/tmp/<TMPSUBDIR>/` | `cycle_run.sh` が実行ごとに作り直す作業領域。**移植元ではない** |

`DET_RUN_UPDATE=2` の step（`src/func_cycle_static.sh`）:

```text
1. scale-rm_pp_ens      SCALE pp
2. scale-rm_init_ens    SCALE init
3. scale-rm_ens         ensemble forecast
4. letkc                mdet を LETKC で更新
5. scale-rm_pp_ens
6. scale-rm_init_ens
7. scale-rm_ens         mdet controlled forecast
8. obsmake
9. obsope
10. letkf               ensemble analysis
11. efso                （有効時のみ）
```

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
| `cycle_run.sh`, `fcst_run.sh`, `src/`, `config.rc` | `run/` から複製 | 中身は変更しない |
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

### 0-5. 実験条件の確定

- `OUTDIR` のパスを決める。
- ノード時間の予算を確認する（792 ノード × cycle 実行時間）。
- 確定値は本書の 1.4 節を更新して記録する。

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
- 1 時間積分にかかる実時間を記録し、1 cycle（ensemble forecast + mdet forecast + LETKC + LETKF）の所要時間を見積もる。
- 48 cycle を1ジョブ（large-o, 最大 48 時間）で流せるかを判断し、`TIME_LIMIT` を決める。

### 完了条件

1 cycle あたりの所要時間の見積もりと、ジョブ分割の方針が決まっている。

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
- `FSTEP=7` まで実行する（最初は `MEMBER=2` で確認してもよい）。

### 最初の重要マイルストーン（M1）

```text
0001–0020 → ensemble forecast → LETKC → mdet → mdet controlled forecast
```

が convection/ の設定で正常終了すること。

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
