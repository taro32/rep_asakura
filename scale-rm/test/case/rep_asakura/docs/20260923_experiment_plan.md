# rep_asakura — case_tc EnKC 実装移植・cycling化 作業計画

改訂: 2026-09-23（配置方針・出力先の一本化・実験規模の仮決定を反映）

## 0. 目的

現在正常に動作している `case_tc` の EnKC（LETKC）cycling 実装を使い、
`rep_asakura` の理想化実験（全陸面・二重周期・BUCKET陸面・放射あり）で
**EnKC を含む cycle を実行できる状態にすること**を目的とする。

この段階では EnKC のアルゴリズムや cycling 構造を新しく設計しない。

```text
既存の case_tc EnKC 実装（letkf_control）
        ↓
依存関係を確認
        ↓
rep_asakura 用のケース設定を letkf_control に追加
        ↓
rep_asakura の初期値生成で、cycle の出力先に直接初期値を作る
        ↓
case_tc と同じ経路で EnKC を実行
        ↓
1 cycle → 2 cycle → 48 時間
```

---

# 1. 決定事項（2026-09-23 時点）

## 1.1 配置方針

| 役割 | 置き場所 | 備考 |
| --- | --- | --- |
| cycle framework（`cycle_run.sh`, `src/`, `config.rc`） | `letkf_control/scale/run/` | **コピーしない**。既存のものをそのまま使う |
| rep_asakura 用 cycle 設定 | `letkf_control/scale/run/config/rep_asakura/` | case_tc と同じ「ケース設定ディレクトリ」として追加 |
| 初期アンサンブル生成スクリプト・テンプレート | `scale-rm/test/case/rep_asakura/` | 既存処理を壊さずに拡張する |
| **計算結果（初期値を含むすべてのデータ）** | **`$OUTDIR` の1か所** | 初期値生成も cycle も同じ `$OUTDIR` に書く |

`cycle_run.sh` は `DIR=$(pwd)/..`、`SCALEDIR=$DIR/../..`、`. ./config.rc`、
`src/`、`ENSMODEL_DIR` / `LETKC_DIR` / `OBSUTIL_DIR` を
`letkf_control/scale/` 基準で解決するため、framework を rep_asakura に
コピーするとパスが壊れる。そのため framework は letkf_control に置いたまま、
ケース設定だけを追加する。

## 1.2 出力先の一本化

出力先は cycle 側の `$OUTDIR` に統一する。

```text
$OUTDIR  （仮: /work/gv42/v42013/20260923_enkc_asakura/result）
├── <STIME>/
│   ├── anal/
│   │   ├── 0001/ … 0020/   init_<STIME>.pe*.nc   ← rep_asakura の初期値生成が直接書く
│   │   └── mdet/           init_<STIME>.pe*.nc   ← 同上
│   └── log/scale_init/<member>/                  ← 初期値生成の LOG
├── <STIME+1h>/ gues/ hist/ anal/ log/ …          ← cycle が書く
├── …
└── obs/
```

- cycle は `MAKEINIT=0` で `$INDIR/$STIME/anal/<member>/init_*.nc` を読む
  （`func_cycle_static.sh` の `RESTART_IN_PATH`）。`INDIR=$OUTDIR` とする。
- rep_asakura の初期値生成は、`init.conf` の `RESTART_OUT_BASENAME` と
  `IO_LOG_BASENAME` を `$OUTDIR` 以下の絶対パスにすることで、
  `letkfinput/` への中間コピー（`preprocess_init.sh`）を不要にする。
- rep_asakura 直下には**スクリプトと設定（ソース）だけ**を置き、データを置かない。

### 既存の初期値生成を壊さないための方針

- `ensinit.sh` は、変数を指定しない場合は従来どおり（`1/`–`101/` に出力）動くようにする。
- 追加する変数（案）:

| 変数 | 既定値（従来動作） | 本実験 |
| --- | --- | --- |
| `MEMBER` | `101` | `21`（20 + mdet） |
| `INIT_TEMPLATE` | `init.conf_base` | `init.conf_base.dx4km`（新規） |
| `OUTROOT` | 空（従来どおりメンバーディレクトリ内に出力） | `$OUTDIR/$STIME` |

- `OUTROOT` を指定した場合、メンバー `1`–`20` を `anal/0001`–`anal/0020`、メンバー `21` を `anal/mdet` に割り当てる。
- 2 km の既存テンプレート（`init.conf_base`, `run.conf`）と既存生成物（`1/`–`101/`, `letkfinput/`）には手を加えない。
  2 km の生成物は格子が変わるので本実験では使わない。扱い（保管・削除）は M1 後に決める。

## 1.3 実験規模（仮案）

先生の助言（格子を粗く、メンバーを減らす）に基づく仮の値。Phase 0 で最終決定する。

| 項目 | 既存 rep_asakura | 本実験（仮） | 備考 |
| --- | --- | --- | --- |
| 水平格子 | 2 km | **4 km**（候補: 5 km） | |
| 領域 | 120 × 120 格子 = 240 km 四方（周期） | 60 × 60 格子 = 240 km 四方（周期） | 領域サイズは維持 |
| MPI 分割 | 12 × 12（IMAX = JMAX = 10） | **6 × 6**（IMAX = JMAX = 10） | 1プロセスあたりの格子数は同じ |
| 鉛直 | KMAX = 64（FZ 同一） | 変更しない | |
| アンサンブル | 101 | **20 + mdet** | env_perturb1–20 → 0001–0020、env_perturb21 → mdet |
| 積分・cycle 期間 | — | **48 時間**（LCYCLE = 3600 s で 48 cycle） | `ETIME = STIME + 48h` |
| 必要ノード数 | — | (20 + 2) × 36 / 4 = **198 ノード** | `DET_RUN=1`, `PPN=4`, `THREADS=12` |

- 5 km にする場合は 48 × 48 格子となり、6 × 6 分割（IMAX = 8）または 4 × 4 分割（IMAX = 12）になる。
- 時間ステップは 2 km 設定（`TIME_DT=6s`, `TIME_DT_ATMOS_DYN=3s`）から比例拡大した値
  （4 km なら `TIME_DT=12s`, `TIME_DT_ATMOS_DYN=6s` を候補）を単独 forecast で安定性確認する。
- 4–5 km は対流のグレーゾーンである。積雲パラメタリゼーションを入れるかどうかは、
  EnKC 移植とは切り離して単独 forecast の段階で判断する。

---

# 2. 移植元（case_tc）の構造

## 2.1 ソースと実行時ディレクトリの区別

| パス | 性質 |
| --- | --- |
| `letkf_control/scale/run/src/` | cycle スクリプト本体（**移植元**） |
| `letkf_control/scale/run/config/case_tc/` | case_tc のケース設定（**移植元**） |
| `letkf_control/scale/run/config.*` | 使用するケースへのシンボリックリンク |
| `letkf_control/scale/tmp/<TMPSUBDIR>/` | `cycle_run.sh` が実行ごとに作り直す作業領域。**移植元ではない** |

`tmp/tropicalcyclone_10/` の中身は `cycle_run.sh` が
`safe_init_tmpdir` と `cp -r src` で生成したものなので、移植元として扱わない。

## 2.2 `DET_RUN_UPDATE=2` の step

`src/func_cycle_static.sh` で定義される順序:

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

---

# 3. member の扱い

```text
0001–0020 : ensemble（LETKC の guess、LETKF の ensemble）
mdet       : deterministic / control（101番目や21番目の member として扱わない）
```

- 初期値生成時の対応: メンバー番号 `21`（env_perturb21）→ `mdet`。
- この対応は `ensinit.sh` の1か所だけで定義し、cycle 内部では `mdet` の名前だけを使う。

---

# 4. 移植対象と分類

| 対象 | 分類 | 内容 |
| --- | --- | --- |
| `run/src/*`, `cycle_run.sh`, `config.rc` | そのまま使う | コピーしない |
| `config.main.Wisteria` | rep_asakura 用に変更 | OUTDIR, OBSIN, SOUNDING, MEMBER, SCALE_NP_X/Y, TMPSUBDIR |
| `config.cycle` | rep_asakura 用に変更 | STIME, ETIME（STIME + 48h）, TIME_LIMIT |
| `config.nml.letkc`, `config.nml.letkf`, `config.nml.obsmake` | 変更（最小限） | 格子・分割数に依存する項目のみ |
| `config.nml.scale`, `config.nml.scale_init` | **新規作成** | rep_asakura の `run.conf` / `init.conf_base` の物理設定を 4 km 化し、case_tc テンプレートの `!--XXX--` マーカーを埋め込む |
| 放射・陸面の静的入力（`PARAG.29`, `PARAPC.29`, `VARDATA.RM29`, `cira.nc`, `MIPAS/`, `param.bucket.conf`） | 既存を利用 | namelist から rep_asakura の絶対パスで参照する（`DISK_MODE=0`） |
| `controltarget`, `OBSIN` | 再生成 | case_tc 格子（25 km, 8 × 4）で作られているため流用不可。M1 用には 4 km 格子のダミーを作る |
| `ensinit.sh` | 拡張 | 1.2 節の変数を追加（既定値で従来動作） |
| `init.conf_base.dx4km` | 新規作成 | 4 km・6 × 6 分割の初期値生成テンプレート |
| 実行ファイル（`scale-rm_*_ens`, `letkc`, `letkf`, `obsmake`, `obsope`） | そのまま使う | letkf_control でビルド済みのもの |

case_tc の namelist は物理設定が大きく異なる（25 km, KMAX = 20, 陸面・放射なし, SF = BULK）。
そのため `config.nml.scale*` は case_tc から「コピーして一部変更」ではなく、
rep_asakura の物理設定を元に作る。

---

# 5. 実装フェーズ

## Phase 0 — 現状保存と実験条件の確定

### 0-1. git の状態を固める

- rep_asakura の未コミット変更（`ensinit.sh`、`WORKFLOW.md` → `docs/`）を確認してコミットする。
- member ディレクトリ・`letkfinput/`・NetCDF・LOG を `.gitignore` に追加する。
- letkf_control 側で staged になっている実行ファイル・NetCDF（`letkc`, `efso`, `scale-rm_*_ens`,
  `merged_history1.pe000000.nc` など）をコミットに含めるかを判断する（含めない場合は `git restore --staged`）。
- タグを付ける: `rep_asakura_pre_enkc`、`case_tc_enkc_working`。

### 0-2. 現在の構成と実行ファイルの記録（`docs/phase0/`）

```bash
mkdir -p docs/phase0
ls -la > docs/phase0/tree.txt
md5sum *.sh *.conf *_base ensperturb/* > docs/phase0/scripts.md5
ls -lL ../../../../bin/scale-rm ../../../../bin/scale-rm_init \
       ../../../../letkf_control/scale/ensmodel/scale-rm_*_ens \
       ../../../../letkf_control/scale/letkc/letkc > docs/phase0/executables.txt
md5sum ../../../../bin/scale-rm ../../../../bin/scale-rm_init >> docs/phase0/executables.txt
```

`../case_tc/scale-rm` と `scale-rm_init` は `bin/` へのシンボリックリンクなので、
letkf_control 側の再ビルドで中身が変わりうる。md5 を記録しておく。

### 0-3. 既存 2 km 生成物の保全

- `letkfinput/`（約 590 GB）と `1/`–`101/` はコピーせず、読み取り専用にする（`chmod -R a-w`）。
- 一覧を残す: `find letkfinput -name '*.nc' -printf '%p %s\n' > docs/phase0/letkfinput_manifest.txt`
- `ensperturb/env_perturb*.txt` がコミット済みであることを確認する（乱数シードは固定されていない）。

### 0-4. 開始時刻（STIME）とスピンアップの確認

- 既存 `run.conf` は `./init_per_SM_R131_0.1_1/perturbed_restart_20000131-000000.000` を読んでいるが、
  このディレクトリは rep_asakura に存在しない。
- 20000131 の restart（30日スピンアップ＋土壌水分摂動と推定）の作成手順と所在を確認する。
- 次のどちらかを決める。
  - (a) 4 km でスピンアップを再現し、スピンアップ後の時刻を STIME とする。
  - (b) 20000101 の初期値から直接 cycle を始める（`STIME=20000101000000`）。
- `ETIME = STIME + 48h` とする。

### 0-5. 実験条件の確定

1.3 節の仮案（4 km, 6 × 6, 20 + mdet, 48 h, 198 ノード）を確定し、
`OUTDIR` のパスを決める。確定値は本書の 1.3 節を更新して記録する。
debug-o / regular-o のノード数・経過時間の上限もここで確認する。

### 完了条件

- 現状（2 km, 101 member の生成処理）がタグと記録から再現できる。
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

### 完了条件

「どのスクリプトが、どの実行ファイルを、どの設定で呼ぶか」が表になっている。

---

## Phase 2 — 4 km 単独 forecast の確認

- `init.conf_base.dx4km` と、4 km 版の単独実行用 `run.conf` を作る。
- 1 member で初期値を作り、短時間の forecast（数時間）を実行する。
- 時間ステップの安定性と、降水・陸面の挙動に明らかな異常がないことを確認する。

### 完了条件

4 km・6 × 6 分割で SCALE-RM が安定に積分できる。

---

## Phase 3 — 初期アンサンブルを OUTDIR に生成

- `ensinit.sh` に `MEMBER` / `INIT_TEMPLATE` / `OUTROOT` を追加する（既定値で従来動作）。
- `MEMBER=21` で実行し、`$OUTDIR/$STIME/anal/{0001..0020,mdet}/` に初期値を直接出力する。
- 従来動作（変数を指定しない場合）が変わっていないことを、生成される `init.conf` の差分で確認する。

### 完了条件

`$OUTDIR/$STIME/anal/` に 20 + mdet の初期値がそろっている。

---

## Phase 4 — rep_asakura ケース設定の作成

- `letkf_control/scale/run/config/rep_asakura/` を作り、1.3・4 節に従って
  `config.main.Wisteria`, `config.cycle`, `config.nml.*` を置く。
- `run/config.*` のシンボリックリンクを rep_asakura に切り替える
  （case_tc の実験を並行する場合は、`run_10/` と同様に `run/` を `run_asakura/` として複製してもよい）。
- `TMPSUBDIR` は case_tc と重ならない名前にする（例: `rep_asakura`）。

---

## Phase 5 — ensemble forecast の接続

`ISTEP=1`, `FSTEP=3` で step 1–3 のみ実行する。

### 完了条件

`$OUTDIR/<STIME+1h>/gues/` に 0001–0020 と mdet の forecast が出力される。

---

## Phase 6 — LETKC と mdet controlled forecast（M1）

- 4 km 格子のダミー controltarget を作る。
- `FSTEP=7` まで実行する。

### 最初の重要マイルストーン（M1）

```text
0001–0020 → ensemble forecast → LETKC → mdet → mdet controlled forecast
```

が rep_asakura の設定で正常終了すること。

---

## Phase 7 — obsmake / OBSOPE / LETKF

- 4 km 格子用の `OBSIN` を作る。
- `FSTEP=10` まで実行し、`0001–0020` の analysis が出ることを確認する。

---

## Phase 8 — 1 cycle → 2 cycle → 48 時間

1. `ETIME = STIME + 1h` で 1 cycle 全体。
2. `ETIME = STIME + 2h` で 2 cycle。analysis → 次 cycle の restart、mdet の引き継ぎ、
   観測・controltarget・history・LETKC 入出力の時刻の整合を確認する。
3. `ETIME = STIME + 48h` で本実行。`TIME_LIMIT` はジョブの経過時間上限であり、
   48 時間の積分に必要な実時間を 2 cycle の実績から見積もって設定する
   （必要なら複数ジョブに分割する）。

---

# 6. テスト戦略

| Test | 内容 | 対応 Phase |
| --- | --- | --- |
| 1 | 4 km 単独 forecast | 2 |
| 2 | 初期アンサンブル生成（OUTDIR 直接出力）と従来動作の維持 | 3 |
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
ensperturb/ と sounding_perturb.py、env_perturb*.txt
既存の 2 km テンプレート（init.conf_base, run.conf）と生成物（1/–101/, letkfinput/）
ensinit.sh の既定動作
letkf_control/scale/run/src/ の cycle 本体
SCALE-RM 本体
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

最終的には、次の cycle を rep_asakura の設定で 48 時間実行できる状態にする。

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
