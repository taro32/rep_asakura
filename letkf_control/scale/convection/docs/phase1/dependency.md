# Phase 1 — case_tc の依存関係（2026-09-25 調査）

`letkf_control/scale/run/`（case_tc）のスクリプトを読んで、
「どのスクリプトが、どの実行ファイルを、どの設定で呼ぶか」をまとめた。
行番号は 2026-09-25 時点のもの。

---

## 1. 全体の流れ

```text
cycle_run.sh（ログインノードで実行）
  ├─ config.main と config.cycle を読む
  ├─ 設定ファイルと実行ファイルを tmp/<TMPSUBDIR>/ にコピーする
  ├─ 全 cycle・全 step の設定ファイル（namelist）をここで先に作る
  └─ ジョブを投入する（rscgrp=regular-o）
        └─ src/cycle.sh（計算ノードで実行）
              └─ cycle ごとに step 1–11 を順に実行する
```

設定ファイルの作り方は、どの step もほぼ同じ。
`config.nml.*` に書かれた `!--XXX--` という目印の次の行に、スクリプトが値（時刻・パスなど）を差し込む。

---

## 2. step の対応表（`DET_RUN_UPDATE=2` のとき）

定義は `src/func_cycle_static.sh` 1698–1745 行、実行の判定は `src/cycle.sh` 200–650 行。

| step | 実行ファイル | 元の設定ファイル | case_tc での動き | 読むもの → 書くもの |
| --- | --- | --- | --- | --- |
| 1 | `scale-rm_pp_ens` | `config.nml.scale_pp` | **飛ばす**（`TOPO_FORMAT='none'` かつ `LANDUSE_FORMAT='none'`） | — |
| 2 | `scale-rm_init_ens` | `config.nml.scale_init` | **飛ばす**（`BDY_FORMAT=5`） | — |
| 3 | `scale-rm_ens` | `config.nml.scale` | 全 member + mean + mdet の 1 時間予報 | `<t>/anal/<m>/init_<t>` → `<t+1h>/anal/<m>/init_<t+1h>`、`<t>/hist/<m>/history` |
| 4 | `letkc` | `config.nml.letkc` + `config.nml.ensmodel` + mean の SCALE 設定 | mdet の初期値を修正する | 読む: `<t>/anal/<m>/init_<t>`、`<t>/hist/<m>/history`、`$OUTDIR/obs/controltarget` → 書く: `<t>/anal/mdet/init_<t>`（**上書き**） |
| 5 | `scale-rm_pp_ens` | step 1 と同じ | **飛ばす** | — |
| 6 | `scale-rm_init_ens` | step 2 と同じ | **飛ばす** | — |
| 7 | `scale-rm_ens` | step 3 と同じ | **step 3 をもう一度全部やり直す**（修正された mdet を含む） | step 3 と同じ |
| 8 | `obsmake` | `config.nml.obsmake` + `config.nml.scale` | mdet の予報から観測を作る | 読む: `<t>/hist/mdet/history`、`OBSIN`（観測地点の一覧）→ 書く: `$OUTDIR/obs/obs_<t+1h>.dat` |
| 9 | `obsope` | — | **飛ばす**（`OBSOPE_RUN=0`。観測演算子は step 10 の中で計算） | — |
| 10 | `letkf` | `config.nml.letkf` + `config.nml.ensmodel` + mean の SCALE 設定 | 0001–0020 の解析 | 読む: `<t+1h>/anal/<m>/init_<t+1h>`、`obs_<t+1h>.dat` → 同じファイルを**上書き** |
| 11 | `efso` | — | **飛ばす**（`EFSO_RUN=0`） | — |

`<t>` は cycle の開始時刻、`<m>` は member 名（0001–0020, mean, mdet）。パスは `$OUTDIR` からの相対パス。

case_tc の実際のジョブログ（`result_1000/case_tc/exp/9103625_cycle_20000101000000/`）でも、
「1・2 飛ばす → 3 → 4 → 5・6 飛ばす → 7 → 8 → 9 飛ばす → 10」の順に動いていることを確認した。

---

## 3. 調べた 4 つの疑問への答え

### 3.1 `scale-rm_init_ens`（step 2, 6）は陸面を上書きしないか → **しない**

`BDY_FORMAT=5` のとき、step 2 と 6 は丸ごと飛ばされる（`src/cycle.sh` 219–226 行）。
cycle の途中で初期値を作り直すことはない。

- `scale-rm_init_ens` が `mod_mkinit.F90` の変更を含まない古い版（2026-06-02 ビルド）でも問題ない。**再ビルドは不要**。
- rep_asakura は全面陸（`LANDUSE_AllLand = .true.`）で地形ファイルを使わないので、step 1・5 も case_tc と同じ条件で飛ばされる。

### 3.2 LETKC / LETKF は陸面変数をどう扱うか → **触らない**

- LETKC・LETKF が読み書きするのは、大気の 11 変数だけ
  （DENS, MOMX, MOMY, MOMZ, RHOT, QV, QC, QR, QI, QS, QG。`common/common_scale.f90` 52 行、`common_nml.f90` の `nv2d = 0`）。
- 解析値は、予報が出力した restart ファイルに**その場で上書き**する（`write_restart` が `NF90_WRITE` で開く）。
  それ以外の変数（土壌水分・土壌温度・地表面温度など）は、各 member の予報結果がそのまま次の cycle に引き継がれる。
- rep_asakura の雲物理は TOMITA08 で、水物質は QV, QC, QR, QI, QS, QG。上の 11 変数とちょうど一致する。

**今後への影響:** 土壌水分を制御対象にするには、LETKC の解析変数に陸面変数を加えるコード変更が必要になる（8 節「まだ決めないこと」で扱う）。

### 3.3 controltarget の形式

- ファイル名は固定で `$OUTDIR/obs/controltarget`（`src/func_cycle_static.sh` 1098–1101 行）。
  **スクリプトはこのファイルを作りもコピーもしない。** 実行前に手で置く必要がある
  （case_tc では 6/29 01:28、ジョブ開始前に置かれていた）。
- 全 cycle で同じファイルを使う（ファイル名に時刻が入らない）。
- 形式は観測ファイルと同じ。Fortran の sequential unformatted で、1 レコードに `real(4)` が 8 個。

  | 番号 | 意味 | case_tc の値 |
  | --- | --- | --- |
  | 1 | 要素番号 | 14593（地上気圧） |
  | 2, 3 | 経度・緯度 | 領域中心の格子点 |
  | 4 | 高さ | 最下層 |
  | 5 | 目標値 | 10.0（hPa） |
  | 6 | 誤差 | 1.0 |
  | 7 | 観測の種類 | 1.0（ADPUPA） |
  | 8 | — | 0.0 |

- 作成プログラムは `run/config/case_tc/make_obsin/controltarget/cntltargetmakein_p.f90`。
  history ファイル（`merged_history1.pe000000.nc`）から格子の経度・緯度を読む。
  2 km 格子用には、2 km 格子の history（Phase 3 の単独予報で出力される）から経度・緯度を読めば、同じ方法で作れる（Phase 6）。

### 3.4 `cycle_run.sh` が `convection/` から使うファイル

`cycle_run.sh` 58–62 行と `staging_list_static`（`src/func_cycle_static.sh` 8–172 行）から。

| コピー元 | コピー先 | 備考 |
| --- | --- | --- |
| `config.nml.*` | `tmp/<TMPSUBDIR>/` | すべて |
| `config.cycle`, `config.fcst`, `config.rc` | 同上 | `config.[c,f,r]*` に当たるもの |
| `config.main.Wisteria` | 同上 | **`config.main` ではない**（4.1 節） |
| `src/` | 同上 | |
| `OBSIN` のファイル | `tmp/<TMPSUBDIR>/obsin/obsin.dat` | |
| 実行ファイル（`../common/`, `../ensmodel/`, `../letkc/`, `../letkf/`, `../obs/`） | `tmp/<TMPSUBDIR>/` | `convection/` からの相対位置は `run/` と同じ |
| `scale-letkc/data/{rad,land,urban,lightning}` | `tmp/<TMPSUBDIR>/dat/` | 4.2 節 |

---

## 4. convection に移すときの注意点

### 4.1 `config.main` と `config.main.Wisteria` は同じファイルにする

`cycle_run.sh` は、投入側では `./config.main` を読むが、ジョブには `config.main.Wisteria` をコピーして使う。
case_tc では `config.main` → `config/case_tc/config.main.Wisteria`（OUTDIR = `result_1000/case_tc`）と
`run/config.main.Wisteria`（OUTDIR = `result/case_tc`）が別のファイルになっていて、OUTDIR が食い違っている。
実際、`result_1000/case_tc/20000101000000/anal/` には mean と mdet しかない。

→ convection では `config.main -> config.main.Wisteria` のシンボリックリンクにして、1 つのファイルだけを編集する（計画書 1.2 節のとおり）。

### 4.2 放射・陸面の入力ファイルは絶対パスで書く

- `config.nml.scale` の目印（`!--ATMOS_PHY_RD_MSTRN_GASPARA_IN_FILENAME--` など）を使うと、
  パスは `$SCALEDIR/scale-rm/test/data/rad/...` になる（`src/func_cycle_static.sh` 740 行）。
  **このディレクトリには放射のファイルがない。** case_tc は放射を使わないので問題にならなかった。
- rep_asakura が使っている `PARAG.29`, `PARAPC.29`, `VARDATA.RM29`, `cira.nc`, `MIPAS/`, `param.bucket.conf` は、
  `scale-letkc/data/rad/`・`data/land/` にあるものと**中身が同じ**（2026-09-25 に `cmp` で確認）。
- → `config.nml.scale` ではこれらの目印を使わず、絶対パスで直接書く。
  参照先は `convection/dat/`（計画書どおりコピーする）か `scale-letkc/data/`（コピー不要）のどちらか。

### 4.3 初期値は OUTDIR に「コピー」する（リンクにしない）

step 4 の LETKC は `<STIME>/anal/mdet/init_<STIME>` を上書きし、step 10 の LETKF は各 member の restart を上書きする。
rep_asakura の `1/`–`21/` へのシンボリックリンクにすると、元のファイルが書き換えられてしまう
（読み取り専用にしてあるので、実際には書き込みエラーで止まる）。
→ Phase 4 では計画書どおりコピーする。

### 4.4 1 cycle の時間は「予報 2 回分」になる

step 7 は step 3 と同じ設定で、全 member・mean・mdet をもう一度計算する（`ensmodel/scale-rm_ens.f90` 118–146 行）。
ノード数は変わらないが、1 cycle の時間は「予報 2 回 + LETKC + obsmake + LETKF」になる。
Phase 3 の見積もりでは、1 時間予報の時間を 2 倍して考える。

### 4.5 ジョブの rscgrp は `regular-o` に固定されている

`cycle_run.sh` 140 行で `#PJM -L "rscgrp=regular-o"` と書かれている。
`debug-o` で動作確認するには、`convection/cycle_run.sh` のこの 1 行を変える必要がある
（計画書 4 節では `cycle_run.sh` を「変更しない」としている）。

### 4.6 その他（後の Phase で確認する）

| 項目 | 内容 | 対応 Phase |
| --- | --- | --- |
| history の出力間隔 | cycle では `!--FILE_HISTORY_DEFAULT_TINTERVAL--` で `CYCLEFOUT` が入る。rep_asakura は 60 秒ごとなので、そのままだとディスクを圧迫する | 5 |
| LETKC の局所化 | case_tc は `HORI_LOCAL = 150 km`。convection の領域は 240 km 四方（周期境界）なので、値の見直しが必要 | 6 |
| OBSIN | 観測地点の一覧。case_tc 用（25 km 格子）なので、2 km 格子用に作り直す | 7 |
| obsmake の地形ファイル | `LETKF_TOPOGRAPHY_IN_BASENAME = $OUTDIR/const/topo/topo` が入るが、このファイルは case_tc にもない。case_tc では問題なく動いている | 7 |

---

## 5. 決める必要があること

1. **放射・陸面の入力ファイルの参照先**（4.2 節）: `convection/dat/` にコピーするか、`scale-letkc/data/` を直接参照するか。
   → **決定（2026-09-25）: `convection/dat/` にコピーする。** 実験に必要なものを convection の中で完結させるため。
   `config.nml.scale` には `convection/dat/` の絶対パスを書く。
2. **`debug-o` での動作確認**（4.5 節）: `convection/cycle_run.sh` の rscgrp の行だけ変えてよいか。
   変えない場合、MEMBER=2（144 ノード）の試験も `regular-o` 経由（small-o 相当）で待つことになる。
   → **Phase 3 の後に決める（2026-09-25）。** debug-o は 30 分で打ち切られるため、
   1 時間予報の実行時間を測ってから、1 cycle（予報 2 回分）が 30 分に収まるかで判断する。
