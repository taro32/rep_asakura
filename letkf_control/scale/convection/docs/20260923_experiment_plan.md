# convection — rep_asakura 設定での EnKC cycle 実験 作業計画

改訂: 2026-09-23（実験ディレクトリを `letkf_control/scale/convection/` に一本化）

## 0. 目的

現在正常に動作している `case_tc` の EnKC（LETKC）cycling 実装を使い、
`rep_asakura` の理想化実験（全陸面・二重周期・BUCKET陸面・放射あり）の設定で
**EnKC を含む cycle を実行できる状態にすること**を目的とする。

この段階では EnKC のアルゴリズムや cycling 構造を新しく設計しない。

```text
既存の case_tc EnKC 実装（letkf_control/scale/run）
        ↓
依存関係を確認
        ↓
letkf_control/scale/convection/ に run/ の framework を複製
        ↓
rep_asakura の初期値生成・物理設定を 4 km 用にして convection/ に持ち込む
        ↓
初期値を OUTDIR に直接生成
        ↓
case_tc と同じ経路で EnKC を実行
        ↓
1 cycle → 2 cycle → 48 時間
```

---

# 1. 決定事項（2026-09-23 時点）

## 1.1 配置方針

新しい実験に必要なスクリプト・設定・入力は、すべて
`letkf_control/scale/convection/` に置く。計算結果はすべて `$OUTDIR` に置く。

| 役割 | 置き場所 | 備考 |
| --- | --- | --- |
| cycle framework（`cycle_run.sh`, `fcst_run.sh`, `src/`, `config.rc`） | `convection/` | `run/` から複製する |
| cycle 設定（`config.main.Wisteria`, `config.cycle`, `config.nml.*`） | `convection/` | rep_asakura の物理設定を 4 km 化して作る |
| 初期アンサンブル生成（スクリプト・テンプレート・摂動サウンディング） | `convection/init/` | rep_asakura の処理を元に作る |
| 放射・陸面の静的入力 | `convection/dat/` | rep_asakura からコピー |
| controltarget・観測入力の作成 | `convection/make_obsin/` | case_tc の `make_obsin/` を元に 4 km 格子用に作り直す |
| 計画書・記録 | `convection/docs/` | |
| **計算結果（初期値を含むすべてのデータ）** | **`$OUTDIR` の1か所** | 初期値生成も cycle も同じ `$OUTDIR` に書く |
| 既存 `run/`（case_tc） | 変更しない | シンボリックリンクも切り替えない |
| 既存 `scale-rm/test/case/rep_asakura/`（2 km・101 member） | 変更しない | 参照元・過去実験として残す |

`convection/` は `run/`・`run_10/`・`run_light/` と同じ階層にある。
`cycle_run.sh` は `DIR=$(pwd)/..`、`SCALEDIR=$DIR/../..` でパスを決めるので、
`convection/` から実行しても `DIR=letkf_control/scale` となり、
実行ファイル（`ensmodel/`, `letkc/`, `letkf/`, `obs/`）の参照は `run/` と同じになる。

## 1.2 ディレクトリ構成

```text
letkf_control/scale/convection/
├── cycle_run.sh, fcst_run.sh, config.rc      ← run/ から複製
├── src/                                      ← run/src から複製
├── config.main.Wisteria                      ← 新規（OUTDIR・MEMBER・格子・分割）
├── config.main -> config.main.Wisteria
├── config.cycle, config.fcst                 ← 新規（STIME・ETIME）
├── config.nml.scale, config.nml.scale_init   ← 新規（rep_asakura 物理 × 4 km）
├── config.nml.letkc, config.nml.letkf,
│   config.nml.obsmake, config.nml.ensmodel,
│   config.obsmake                            ← case_tc から複製して最小限変更
├── init/
│   ├── ensinit.sh                            ← 4 km・OUTDIR 直接出力版
│   ├── init.conf_base                        ← 4 km・6×6 分割のテンプレート
│   ├── init.sh_base
│   └── ensperturb/                           ← env.txt, env_perturb1–21.txt, sounding_perturb.py
├── dat/                                      ← PARAG.29, PARAPC.29, VARDATA.RM29, cira.nc, MIPAS/, param.bucket.conf
├── make_obsin/                               ← controltarget・OBSIN 作成（4 km 格子用）
└── docs/                                     ← 本書・Phase 0 の記録

$OUTDIR  （仮: /work/gv42/v42013/20260923_enkc_convection/result）
├── <STIME>/
│   ├── anal/
│   │   ├── 0001/ … 0020/   init_<STIME>.pe*.nc   ← init/ensinit.sh が直接書く
│   │   └── mdet/           init_<STIME>.pe*.nc
│   └── log/scale_init/<member>/                  ← 初期値生成の LOG
├── <STIME+1h>/ gues/ hist/ anal/ log/ …          ← cycle が書く
├── …
└── obs/

letkf_control/scale/tmp/convection/               ← cycle_run.sh が毎回作り直す作業領域（TMPSUBDIR）
```

## 1.3 初期値生成と cycle のつなぎ方

- cycle は `MAKEINIT=0` で `$INDIR/$STIME/anal/<member>/init_*.nc` を読む
  （`src/func_cycle_static.sh` の `RESTART_IN_PATH`）。`INDIR=$OUTDIR` とする。
- `init/ensinit.sh` は `../config.main` と `../config.cycle` を読み込み、
  `OUTDIR`・`STIME`・`MEMBER` を cycle と共通の値で使う（設定の二重管理をしない）。
- 各メンバーの `init.conf` では `RESTART_OUT_BASENAME` と `IO_LOG_BASENAME` を
  `$OUTDIR/$STIME/...` の絶対パスにする。静的入力は `convection/dat/` の絶対パスで参照する。
- メンバー対応: `env_perturb1–20` → `0001–0020`、`env_perturb21` → `mdet`。
  この対応は `ensinit.sh` の1か所だけで定義する。
- 初期値生成に使う `scale-rm_init` は、`SCALEDIR/bin/scale-rm_init` を絶対パスで指定する。
- `init/` 以下の作業ディレクトリには、生成した `init.conf` / `init.sh` だけが残り、データは置かない。

## 1.4 実験規模（仮案）

先生の助言（格子を粗く、メンバーを減らす）に基づく仮の値。Phase 0 で最終決定する。

| 項目 | 既存 rep_asakura | convection（仮） | 備考 |
| --- | --- | --- | --- |
| 水平格子 | 2 km | **4 km**（候補: 5 km） | |
| 領域 | 120 × 120 格子 = 240 km 四方（周期） | 60 × 60 格子 = 240 km 四方（周期） | 領域サイズは維持 |
| MPI 分割 | 12 × 12（IMAX = JMAX = 10） | **6 × 6**（IMAX = JMAX = 10） | 1プロセスあたりの格子数は同じ |
| 鉛直 | KMAX = 64（FZ 同一） | 変更しない | |
| アンサンブル | 101 | **20 + mdet** | |
| cycle 期間 | — | **48 時間**（LCYCLE = 3600 s で 48 cycle） | `ETIME = STIME + 48h` |
| 必要ノード数 | — | (20 + 2) × 36 / 4 = **198 ノード** | `DET_RUN=1`, `PPN=4`, `THREADS=12` |

- 5 km にする場合は 48 × 48 格子となり、6 × 6 分割（IMAX = 8）または 4 × 4 分割（IMAX = 12）になる。
- 時間ステップは 2 km 設定（`TIME_DT=6s`, `TIME_DT_ATMOS_DYN=3s`）から比例拡大した値
  （4 km なら `TIME_DT=12s`, `TIME_DT_ATMOS_DYN=6s` を候補）を単独 forecast で安定性確認する。
- 4–5 km は対流のグレーゾーンである。積雲パラメタリゼーションを入れるかどうかは、
  EnKC 移植とは切り離して単独 forecast の段階で判断する。
- `TIME_LIMIT`（ジョブの経過時間上限）は cycle 期間とは別の値であり、Phase 8 で実績から決める。

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

## 2.2 rep_asakura（物理設定・初期値生成）

| rep_asakura のファイル | convection での扱い |
| --- | --- |
| `init.conf_base` | 4 km・6 × 6 に変更して `init/init.conf_base` と `config.nml.scale_init` の元にする |
| `run.conf` | 4 km・時間ステップを変更して `config.nml.scale` の元にする |
| `ensinit.sh`, `init.sh_base` | `init/` に OUTDIR 直接出力版として作る |
| `ensperturb/`（env.txt, env_perturb1–21, sounding_perturb.py） | `init/ensperturb/` にコピー（乱数を振り直さない） |
| 静的入力（PARAG.29 など） | `dat/` にコピー |
| `preprocess_init.sh`, `letkfinput/` | 使わない（OUTDIR に直接出力するため不要） |

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
| `config.main.Wisteria` | 新規 | OUTDIR, OBSIN, SOUNDING, MEMBER=20, SCALE_NP_X/Y=6, TMPSUBDIR=convection |
| `config.cycle`, `config.fcst` | 新規 | STIME, ETIME（STIME + 48h）, TIME_LIMIT |
| `config.nml.scale`, `config.nml.scale_init` | 新規 | rep_asakura の物理設定 × 4 km、case_tc テンプレートの `!--XXX--` マーカーを埋め込む |
| `config.nml.letkc`, `config.nml.letkf`, `config.nml.obsmake`, `config.nml.ensmodel`, `config.obsmake` | case_tc から複製して変更 | 格子・分割数・メンバー数に依存する項目のみ |
| `init/*` | 新規 | 1.3 節のとおり |
| `dat/*` | rep_asakura からコピー | |
| `make_obsin/`（controltarget, OBSIN） | 作り直し | case_tc 格子（25 km, 8 × 4）用なので流用不可。M1 用には 4 km 格子のダミーを作る |
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

- rep_asakura の `letkfinput/`（約 590 GB）と `1/`–`101/` はコピーせず、読み取り専用にする（`chmod -R a-w`）。
- 一覧を残す: `find letkfinput -name '*.nc' -printf '%p %s\n'` の出力を `docs/phase0/` に保存する。
- `ensperturb/env_perturb*.txt` がコミット済みであることを確認する（乱数シードは固定されていない）。

### 0-4. 開始時刻（STIME）とスピンアップの確認

- rep_asakura の `run.conf` は `./init_per_SM_R131_0.1_1/perturbed_restart_20000131-000000.000` を読んでいるが、
  このディレクトリは rep_asakura に存在しない。
- 20000131 の restart（30日スピンアップ＋土壌水分摂動と推定）の作成手順と所在を確認する。
- 次のどちらかを決める。
  - (a) 4 km でスピンアップを再現し、スピンアップ後の時刻を STIME とする。
  - (b) 20000101 の初期値から直接 cycle を始める（`STIME=20000101000000`）。
- `ETIME = STIME + 48h` とする。

### 0-5. 実験条件の確定

1.4 節の仮案（4 km, 6 × 6, 20 + mdet, 48 h, 198 ノード）を確定し、`OUTDIR` のパスを決める。
確定値は本書の 1.4 節を更新して記録する。
debug-o / regular-o のノード数・経過時間の上限もここで確認する。

### 完了条件

- 既存の rep_asakura（2 km, 101 member）と case_tc がタグと記録から再現できる。
- STIME / ETIME / 格子 / 分割 / メンバー数 / OUTDIR が決まっている。

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
```

### 完了条件

`convection/` に 1.2 節の構成（設定ファイルの中身は未作成）がそろっている。

---

## Phase 3 — 4 km 単独 forecast の確認

- `init/init.conf_base`（4 km・6 × 6）と、単独実行用の forecast 設定を作る。
- 1 member で初期値を作り、短時間の forecast（数時間）を実行する。
- 時間ステップの安定性と、降水・陸面の挙動に明らかな異常がないことを確認する。

### 完了条件

4 km・6 × 6 分割で SCALE-RM が安定に積分できる。

---

## Phase 4 — 初期アンサンブルを OUTDIR に生成

- `init/ensinit.sh` を 1.3 節のとおり作る。
- `MEMBER=21` で実行し、`$OUTDIR/$STIME/anal/{0001..0020,mdet}/` に初期値を直接出力する。

### 完了条件

`$OUTDIR/$STIME/anal/` に 20 + mdet の初期値がそろっている。

---

## Phase 5 — cycle 設定の作成と ensemble forecast の接続

- 4 節の分類に従って `config.main.Wisteria`, `config.cycle`, `config.nml.*` を作る。
- `ISTEP=1`, `FSTEP=3` で step 1–3 のみ実行する。

### 完了条件

`$OUTDIR/<STIME+1h>/gues/` に 0001–0020 と mdet の forecast が出力される。

---

## Phase 6 — LETKC と mdet controlled forecast（M1）

- `make_obsin/` で 4 km 格子のダミー controltarget を作る。
- `FSTEP=7` まで実行する。

### 最初の重要マイルストーン（M1）

```text
0001–0020 → ensemble forecast → LETKC → mdet → mdet controlled forecast
```

が convection/ の設定で正常終了すること。

---

## Phase 7 — obsmake / OBSOPE / LETKF

- `make_obsin/` で 4 km 格子用の `OBSIN` を作る。
- `FSTEP=10` まで実行し、`0001–0020` の analysis が出ることを確認する。

---

## Phase 8 — 1 cycle → 2 cycle → 48 時間

1. `ETIME = STIME + 1h` で 1 cycle 全体。
2. `ETIME = STIME + 2h` で 2 cycle。analysis → 次 cycle の restart、mdet の引き継ぎ、
   観測・controltarget・history・LETKC 入出力の時刻の整合を確認する。
3. `ETIME = STIME + 48h` で本実行。`TIME_LIMIT` は 2 cycle の実績から見積もって設定する
   （必要なら複数ジョブに分割する）。

---

# 6. テスト戦略

| Test | 内容 | 対応 Phase |
| --- | --- | --- |
| 1 | 4 km 単独 forecast | 3 |
| 2 | 初期アンサンブル生成（OUTDIR 直接出力） | 4 |
| 3 | ensemble forecast（step 1–3） | 5 |
| 4 | LETKC + mdet controlled forecast（**M1**） | 6 |
| 5 | obsmake | 7 |
| 6 | OBSOPE / LETKF | 7 |
| 7 | 1 cycle | 8 |
| 8 | 2 cycle | 8 |
| 9 | 48 時間 | 8 |

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
- 格子 4 km / 5 km、メンバー数、期間の本決定（本書の値は仮案）

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
