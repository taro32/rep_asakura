# Phase 6 — LETKC と mdet の制御付き予報（M1）

## 方針（2026-09-26 決定）

- M1 は **制御なし** の controltarget（地上気圧 10 hPa）で通す。
  LETKC は「目標値 − モデルの値」が負の目標を捨てるので、制御は一度もかからない（`docs/phase1/dependency.md` 3.3 節）。
- M1 が通った後に、controltarget（対流性降雨向けの指標）と制御の中身を変えていく（計画書 8.1 節）。
- MEMBER = 20、regular-o（large-o）で行う。

## 準備したもの

### controltarget

`convection/make_obsin/controltarget/make_controltarget.py nocontrol --install` で作り、`$OUTDIR/obs/controltarget` に置いた。

| 項目 | 値 |
| --- | --- |
| 要素 | 14593（地上気圧） |
| 位置 | 領域中心の格子点（全体の格子番号 60, 60）。経度・緯度とも -0.008993°、高さ 37.5 m（最下層） |
| 目標値・誤差 | 10.0 hPa・1.0 hPa |
| 観測の種類 | 1.0（ADPUPA） |
| 形式 | case_tc の `controltarget_10` と同じ（40 バイト、リトルエンディアン、real(4) × 8） |

目標地点の地上気圧は約 1000 hPa（step 3 の history で 0 分 1000.12 hPa、60 分 999.98 hPa）なので、10 hPa の目標は必ず捨てられる。

### `config.nml.letkc`

- `HORI_LOCAL` を 150 km → **20 km（仮）** にした。影響は約 73 km 先でゼロになる。
  case_tc の 150 km では約 550 km 先まで届き、240 km 四方の領域全体が対象になるため。
  制御なしでは結果に影響しない。制御指標を決めるときに見直す。
- それ以外は case_tc と同じ。

### 比較用の step 3 の結果

step 7 は step 3 の出力（`20000101010000/anal/`、`20000101000000/hist/`）を上書きするので、
MEMBER=20 の step 3 試験（ジョブ 9719073）の 1 時間後の restart を
`$OUTDIR/ref_step3_9719073/20000101010000/anal/{mdet,mean,0001,0020}/` に取っておいた。

## M1a（配管の確認）で実行するもの

M1 は M1a（制御なし・配管）と M1b（制御あり・制御の本体）の 2 段階に分ける（計画書 Phase 6）。ここからは M1a。

```bash
cd /work/02/gv42/v42013/scale-letkc/letkf_control/scale/convection
./cycle_run.sh 20000101000000 20000101000000 1 7 static 00:30:00
```

1 cycle 分の step 1–7。実際に動くのは step 3（予報）・step 4（LETKC）・step 7（予報のやり直し）。

## 確認すること

1. step 4（LETKC）と step 7 が正常に終わる。
2. **制御なしなので、step 7 の mdet の 1 時間後の restart が、step 3（比較用）と完全に一致する。**
3. 0001〜0020・mean も一致するか（LETKC が members を書き直すと、丸め誤差で変わる可能性がある）。
4. STIME の初期値（`20000101000000/anal/`）が LETKC で書き換えられたかどうか（md5 を `docs/phase0/init_1-21.md5` と比べる）。

## 注意: やり直すとき

LETKC は STIME の `anal/mdet/`（と、場合によっては他の member）をその場で上書きする。
同じ試験をやり直すときは、STIME の初期値を取り込み直す:

```bash
rm -rf /work/gv42/v42013/20260923_enkc_convection/result/20000101000000/anal
cd /work/02/gv42/v42013/scale-letkc/letkf_control/scale/convection/init && ./import_rep_asakura.sh
```

## M1a の記録

### 1 回目（2026-09-26 19:26、ジョブ 9731138）— LETKC が途中で異常終了

| 確認したこと | 結果 |
| --- | --- |
| ジョブ | large-o・840 ノード、経過 1 分 27 秒。最後に `SCALE-LETKF successfully completed` が出た |
| 各 step の時間 | step 3: 23 秒、（ファイルのコピー 32 秒）、step 4 LETKC: 15 秒、step 7: 16 秒 |
| **LETKC** | **全 144 プロセスが `No such file or directory` → `stop 10` で異常終了していた**。cycle スクリプトはこれを検出せず、step 7 に進んだ |
| 目標の判定 | 止まる前の統計で、地上気圧の目標を受け入れた数は **0**（10 hPa の目標は設計どおり捨てられた） |
| step 7 の結果 | mdet・mean・0001・0020 の 1 時間後の restart が step 3（比較用）と完全に一致。ただし LETKC が何も書かずに止まったためで、合格の根拠にはならない |
| STIME の `anal/` | LETKC は書き換えていない（ファイルの時刻は Phase 4 の取り込み時のまま） |

**原因:** LETKC は出力ファイルを「既存のファイルを開いて上書きする」方式で書くので、書き出し先のファイルを事前に用意しておく必要がある。
step 4 の準備（`src/cycle.sh` 467–469 行、`SPRD_OUT=1` のとき）で、

```bash
mkdir -p $OUTDIR/$atime/anal/sprd              # 次の時刻（atime）に作っている
cp -r $BGDIR/anal/mean/* $OUTDIR/$time/anal/sprd/   # 今の時刻（time）にコピーしようとしている
```

と時刻が食い違っているため、今の時刻の `anal/sprd` が用意されない。続く処理で `anal/sprd` → `gues/sprd` のコピーも失敗し
（ログの `cp: cannot stat '.../20000101000000/anal/sprd/*'`）、LETKC は背景場のばらつきを空の `gues/sprd` に書こうとして止まった
（`letkc/letkf.f90` 163 行、`write_enssprd(GUES_SPRD_OUT_BASENAME, ...)`。`das_letkf` の前）。

**case_tc でも同じ:** case_tc のジョブ（9032180, 9103625, 9165602）でも、最初の cycle だけ `stop 10`（32 プロセス分）と
`anal/sprd` のコピー失敗が 1 回ずつ出ていた。2 cycle 目以降は、前の cycle の LETKF が次の時刻の `anal/sprd` を作るので起きない。
**つまり case_tc でも、最初の cycle の LETKC は毎回止まっていた**（制御なしの実行だったので結果には影響がない）。

**注意:** LETKC が異常終了しても、cycle スクリプトは止まらずに次の step に進み、最後に `successfully completed` と出る。
LETKC の成否は、ジョブのログに `stop 10` がないことで確かめる必要がある。

**対処（2026-09-26）:** `convection/src/cycle.sh` 468 行目の `mkdir -p $OUTDIR/$atime/anal/sprd` を `$time` に直した（`run/` からの変更）。
- 469 行目の `cp` の書き先、LETKC が書くばらつきのファイル（`ANAL_SPRD_OUT_BASENAME` は省略時 `ANAL_OUT_BASENAME` と同じで `$time/anal/sprd`）、
  途中の step から再開するときの準備（`src/func_cycle_static.sh` 1169 行）がすべて `$time` なので、`$atime` は書き間違いと判断した。
- step 10（LETKF）の準備（`src/cycle.sh` 527–528 行）は `mkdir` も `cp` も `$atime` でそろっていて、影響を受けない。
- 初期値の取り込みで `anal/sprd` を用意する案もあったが、不具合が残り、初期値を作り直すたびに用意を忘れると
  最初の cycle の制御が黙って抜けるので、cycle 本体を直す方を選んだ。
- 1 回目の実行では LETKC が STIME の `anal/` を書き換える前に止まったので、初期値を取り込み直さずにそのまま再実行できる。

### 2 回目（2026-09-26 19:34、ジョブ 9731187）— 合格

`src/cycle.sh` 468 行を直してから、初期値を取り込み直さずに同じコマンドで投入した。

| 確認したこと | 結果 |
| --- | --- |
| ジョブ | large-o・840 ノード、経過 2 分 39 秒 |
| 各 step の時間 | step 3: 20 秒、（ファイルのコピー 1 分 45 秒）、step 4 LETKC: 16 秒、step 7: 17 秒 |
| LETKC | **最後まで正常に動いた**。ログに `stop` も `cannot stat` もない |
| 目標の判定 | 地上気圧の目標を受け入れた数は 0（制御なし） |
| LETKC の出力 | STIME の `anal/{0001..0020,mean,mdet,sprd}/` と `gues/{mean,sprd}/` を書いた（19:36:43–44） |
| 書き直された初期値（0001, 0020, mdet） | 元の値（rep_asakura）と比べて、DENS に 4.4e-16、RHOT に 1.7e-13 の差があるだけ。ほかの 11 変数は完全に同じ |
| 書き直された mean・sprd | 20 member の平均・標準偏差と一致（差 1e-18 程度） |
| step 7 と step 3（比較用）の 1 時間後の差 | mdet: MOMZ 0.044、RHOT 0.087、QV 4.7e-4。0020 も同程度、0001 は 1 桁小さい。mean は初期値が変わったので大きく違う（MOMZ 6.9） |

**step 7 が step 3 と完全に一致しなかった理由:** LETKC は制御がかからないときも初期値を読んで書き直し、
その変換で DENS・RHOT に丸め誤差（1e-13 程度）が入る。対流がこれを増幅して、1 時間後に上の程度の差になった。
member どうしの違い（MOMZ で 2〜6）の 1〜2% 程度。

**合格条件の見直し（2026-09-26）:** 「step 7 の mdet が step 3 と完全に一致する」は、LETKC が丸め誤差を入れる以上そもそも満たせなかった。
「step 1–7 が異常終了なしで通り、LETKC で書き直された mdet の初期値が元の値と丸め誤差（1e-12 以下）の範囲で一致する」に改めた。
この条件で M1a は合格。

**制御あり・なしを比べるときの雑音の目安:** 制御なしでも、LETKC の丸め誤差が 1 時間で mdet に
MOMZ 0.04、RHOT 0.09 K 程度の差を生む。制御の効果はこれより十分大きい必要がある。

**STIME の初期値:** LETKC が書き直したので、md5 は Phase 0 の記録と一致しなくなった（値は丸め誤差の範囲で同じ）。

## 制御前の mdet を取っておく（2026-09-26）

LETKC は時刻 t の初期値（`<t>/anal/<member>/init_<t>`）を読み、同じファイルに上書きする。
そのままでは制御前の mdet が残らないので、`src/cycle.sh` の step 4 の準備に、
LETKC の直前に `anal/mdet/` を `gues/mdet/` にコピーする処理を加えた（`run/` からの変更）。

- `<t>/gues/mdet/init_<t>` が制御前、`<t>/anal/mdet/init_<t>` が制御後。差がその cycle の修正量。
- 1 cycle 約 140 MB、48 cycle で約 7 GB。
- `gues/` の下で LETKC・LETKF が使うのは `mean` と `sprd` だけで、ぶつからない。
- 途中の step から再開するとき（`ISTEP > 3`）の準備（`src/func_cycle_static.sh` 1160–1166 行）は `gues/mdet/` を `anal/mdet/` に戻す作りで、
  もともと `gues/mdet` に制御前の mdet がある前提だった。今回の追加で、step 4 からのやり直しも正しく動く。
- 元々の仕組みには修正前の全 member を `gues/` に取っておく処理があるが、case_tc で止められていた（`omiting the copy of gues files`）。
  0001〜0020 は LETKC で変わらないので、mdet だけを取っておく。
- 正しく働くかは M1b の試験で一緒に確かめる。

## M1b（制御の本体）の準備（2026-09-26）

### 目標値の決め方

M1b は「制御の計算が実際に働くか」を確かめる試験なので、目標値と誤差をアンサンブルのばらつきと同じくらいの大きさにする。

- 目標地点（領域中心）の 60 分の地上気圧（M1a の予報）: mdet 999.978、20 member 平均 999.995、ばらつき 0.0115 hPa。
- 孤立積乱雲の冷気プールによる地上気圧の上昇は一般に +1〜3 hPa 程度だが、今回の予報の 60 分は雨が降り始めたところで、
  領域平均からのずれは −0.11〜+0.14 hPa しかない。
- 目標の誤差 1 hPa・ずれ +1 hPa にすると、LETKC が目標に寄せる割合は (0.0115)² / (0.0115² + 1²) ≈ 0.01% しかなく、
  修正は M1a の丸め誤差の雑音に埋もれる。

→ **目標値 1000.03 hPa、誤差 0.01 hPa**（member 平均より +0.035、mdet より +0.05 hPa。ばらつきの 3〜4 倍）。
指標として選んだ値ではない。

### 高さを 0 m にした

地上気圧の目標では、LETKC はモデルの地上気圧（SFC_PRES）を controltarget の「高さ」に換算してから目標と比べる
（`common_letkc/common_obs_scale.f90` の `prsadj`。高さの単位は m のまま使われる）。
制御なしの controltarget（case_tc と同じく最下層の高さ 37.5 m）では、モデル側の値が約 4.3 hPa 低く換算される。
M1b では高さを 0 m にして換算をなくし、SFC_PRES とそのまま比べるようにした（地形はない）。

`make_controltarget.py ctltest --install` で作り、`$OUTDIR/obs/controltarget` に置いた。
制御なしの `controltarget_nocontrol` はスクリプトの変更後も同じ中身で作られることを確認した。

### STIME の初期値を取り込み直した

M1a で LETKC が書き直した（丸め誤差が入った）ので、`20000101000000/anal/` と `gues/` を消して取り込み直した。
22 member × 144 ファイルすべての md5 が `docs/phase0/init_1-21.md5` と一致した。

このとき `import_rep_asakura.sh` が、OUTDIR を `../config.main` から読む経路で失敗した
（スクリプトは `set -u` で動いていて、`config.main` の中の未定義の変数 `SCALE_DB` で止まった）。
`config.main`・`config.cycle` を読むところだけ `set +u` にして直した。Phase 4 では OUTDIR を引数で渡したので、この経路は通っていなかった。

## M1b で実行するもの

```bash
cd /work/02/gv42/v42013/scale-letkc/letkf_control/scale/convection
./cycle_run.sh 20000101000000 20000101000000 1 7 static 00:30:00
```

M1a と同じコマンド。違うのは `$OUTDIR/obs/controltarget` の中身だけ。

## M1b の記録

### 1 回目（2026-09-26 20:06、ジョブ 9731386）— 動いたが、制御がかからなかった

| 確認したこと | 結果 |
| --- | --- |
| ジョブ | large-o・840 ノード、経過 3 分 9 秒。`stop`・`cannot stat` なし |
| 各 step の時間 | step 3: 22 秒、（ファイルのコピー 2 分 14 秒）、step 4 LETKC: 16 秒、step 7: 16 秒 |
| 制御前の mdet の保存 | `20000101000000/gues/mdet/` に 144 ファイル（20:06:56）。LETKC の前に保存された |
| 目標の判定 | 地上気圧の目標を**受け入れた数は 1**。背景場とのずれの統計は BIAS −3.288 Pa（目標と 20 member 平均の差 0.033 hPa に相当） |
| **mdet の修正量**（`anal/mdet` − `gues/mdet`） | **すべての変数・すべての格子でゼロ**（DENS 4.4e-16、RHOT 1.7e-13 の丸め誤差だけ。M1a と同じ） |
| 0001・0020 | 元の初期値と丸め誤差の範囲で一致（変わっていない） |

**原因の調査（まだ特定できていない）**

| 疑ったこと | 結果 |
| --- | --- |
| 目標が捨てられた | ×。受け入れた数 1。`obsda%val`（目標 − 20 member 平均）は正 |
| `force_check`（水蒸気を増やす修正を捨てる。`letkf_tools.f90` 63 行で固定で有効） | ×（の可能性が高い）。0 分の最下層の QV と 60 分の目標地点の地上気圧の相関は、目標から 73 km 以内のすべての格子で負（約 −0.02）。気圧を上げるには QV を減らす向きになり、捨てられないはず |
| mdet を更新しない設定 | ×。LETKC に渡された `DET_RUN_UPDATE = .true.` |
| 境界の緩衝帯（`relax_beta`） | ×。`BOUNDARY_BUFFER_WIDTH = 0` なので β = 1 |
| 変数ごとの重みの使い回し（`var_local_n2nc`） | ×。局所化の表の書き換え（143–146 行）の後に作られている |
| 最下層の QV に member 間のばらつきがない | ×。0.15 g/kg ある（水平に一様） |

素朴な見積もり（目標 1 つの EnKF）では、目標地点の最下層の QV の修正は
相関 −0.02 × ばらつき 0.15 g/kg × 1.15 Pa / (1.15² + 1²) Pa × 5.2 Pa ≈ −0.008 g/kg 程度になり、ゼロにはならないはず。

### 別に見つかった問題: 初期値の摂動が member の番号とともに積み重なっている

`init/ensperturb/sounding_perturb.py`（rep_asakura から複製）は

```python
copy = data
copy[0:13,2] = copy[0:13,2] + random_matrix
```

としていて、`copy = data` はコピーではなく同じ配列を指すので、**摂動が member ごとに足し合わされていく**。
`env_perturb<i>.txt` と `env.txt` の水蒸気（下層 13 行）の差の大きさ（RMS）は、
member 1 で 0.10、member 10 で 0.21、member 20 で 0.44、member 21（mdet）で 0.42 g/kg。
1 つ前の member との差は、指定どおり 0.1 g/kg（標準偏差）になっている。

- アンサンブルのばらつきは「平均のまわりの独立な揺らぎ」ではなく、番号順に広がる酔歩（ランダムウォーク）になっている。
- mdet（21）も摂動が大きい側にいる。
- M1b の結果（制御がかからない）との関係は不明。アンサンブルの性質として、後で直すかどうかを決める。

### 2 回目（診断用）の準備（2026-09-26）

LETKC の実行ファイルは case_tc と共有しているので作り直さず、設定だけで診断情報を増やす。

- `config.nml.letkc`: `LOG_LEVEL` を 1 → **3**（目標 1 つごとの判定の詳細をログに出す）。調査が終わったら 1 に戻す。
- `config.cycle`: `NOBS_OUT` を 0 → **1**（各格子点で使われた目標の数を `tmp/convection/nobs.d01_<time>.pe*.nc` に出す。
  `CLEAR_TMP=0` なので作業領域はジョブの後も残る）。調査が終わったら 0 に戻す。
- **`src/cycle.sh` 504 行の不具合を修正:** `NOBS_OUT=1` のとき、step 4 の準備は `$TMP/nobs.d01_<atime>` を用意するが、
  LETKC の `NOBS_OUT_BASENAME` は `nobs.d01_<time>`（`src/func_cycle_static.sh` 1272 行）で、時刻が食い違う。
  `anal/sprd`（468 行）と同じ種類の不具合で、このままだと LETKC が止まる。コピー先を `$time` に直した（`run/` からの変更）。
  制御なしの LETKF の経路（422 行）と step 10（563 行）は、準備と設定の時刻がそろっている。
- STIME の初期値を取り込み直した（22 member すべて md5 一致）。controltarget は 1 回目と同じ `controltarget_ctltest`。

### 2 回目（診断用、2026-09-26 20:25、ジョブ 9731508）— 原因の一部が判明

`LOG_LEVEL=3`、`NOBS_OUT=1`。ジョブは 4 分 19 秒で正常終了（LETKC はログが増えて 70 秒）。制御は今回もかからなかった。

**判明 1: LETKC が目標を 60 分ではなく 10 分の予報と比べていた。**

- LETKC は history を読むとき、スロットの番号をそのまま history の何番目の時刻かとして使う
  （`common_letkc/common_mpi_scale.f90` 2381・2444 行、`read_ens_history_iter(it, islot, ...)` → `read_history(filename, step, ...)`）。
- LETKC に渡された設定は `SLOT_START=1, SLOT_END=2, SLOT_BASE=2, SLOT_TINTERVAL=3600`（`LTIMESLOT=3600`）で、目標はスロット 2（60 分）。
- case_tc は history が 1 時間ごと（0, 60 分の 2 回）だったので「スロット 2 = 2 番目 = 60 分」で正しかった。
  convection は Phase 5 で history を 10 分ごと（`FCSTOUT=600`、0, 10, …, 60 分の 7 回）にしたので、「スロット 2 = 2 番目 = **10 分**」になった。
- 数字でも確認した。目標地点の 20 member 平均の地上気圧は、history の 2 番目（10 分）で 999.9972 hPa、
  目標 1000.03 hPa（real(4) で 1000.030029）との差 3.2876 Pa がログの値と一致する（7 番目の 60 分なら 3.5 Pa）。
- M1b は 60 分の予報を見て目標を決めたので、この食い違いは直す必要がある。
  step 8（obsmake）と step 10（LETKF）も同じ読み方をしている可能性がある（Phase 7 で確認）。

**判明 2: 目標は受け入れられたが、どの格子点の計算にも使われていない。**

- ログの 1 行（要素・種類・経度・緯度・高さ・目標値・誤差・差・QC）: `14593 1 -0.01 -0.01 0.0000 100003.0000 1.0000 -3.2876 0`。QC は 0（良）。
- 目標は領域中心を受け持つプロセス 65 に、スロット 2 の目標として 1 つ割り当てられていた。
- **`nobs`（各格子点で使われた目標の数）は、領域全体・全変数でゼロ。**
  つまり、修正が後で消されたのではなく、そもそも各格子点の計算に目標が入っていない。
- 原因はまだ分からない。M1b で変えたこと（目標の高さを 37.5 m → 0 m）が関係している可能性がある
  （地上気圧の目標では、高さはそのまま縦の位置 `rk` として使われる。`phys2ijk` の `rk = rlev`）。
  ただし、LETKC のソースの中に、縦の位置で目標を外す処理は見つかっていない。

### 3 回目の準備（2026-09-26）— 判明 1 の対策と判明 2 の切り分けを同時に行う

1. **`config.main.Wisteria` の `LTIMESLOT` を 3600 → 600**（判明 1 の対策）。
   スロットは 0, 10, …, 60 分の 7 つになり（`SLOT_START=1, SLOT_END=7, SLOT_BASE=7`。`src/func_cycle_static.sh` の `obstime`）、
   「スロット k = history の k 番目の時刻」と正しく対応する。history の初期時刻出力（`FILE_HISTORY_OUTPUT_STEP0 = .true.`）が前提。
   history の出力間隔（`FCSTOUT=600`）は変わらない。
2. **目標の高さを case_tc と同じ最下層（37.5 m）に戻す**（判明 2 の切り分け）。`controltarget_ctltest_lev1`。
   LETKC はモデルの地上気圧を 37.5 m に換算して比べる（`prsadj`）ので、目標値も換算後の値で決めた。
   60 分の目標地点の換算値は 20 member 平均 99576.03 Pa（ばらつき 1.26 Pa）、mdet 99574.35 Pa（換算前の SFC_PRES の平均は 99999.49 Pa）。
   → 目標値 **995.795 hPa**（平均 + 約 3.5 Pa、mdet + 5.2 Pa）、誤差 0.01 hPa。
3. 診断用の設定（`LOG_LEVEL=3`、`NOBS_OUT=1`）はそのまま。STIME の初期値を取り込み直した。

2 つを同時に変えたので、制御がかかっても、どちらが効いたかは分からない（2026-09-26 にユーザーと合意）。

### 3 回目（2026-09-26 20:37、ジョブ 9731576）— 制御がかかった

`LTIMESLOT=600`、目標の高さ 37.5 m（`controltarget_ctltest_lev1`、目標値 995.795 hPa）。ジョブは 4 分 22 秒で正常終了（`stop`・`cannot stat` なし）。

| 確認したこと | 結果 |
| --- | --- |
| スロット | `SLOT_START=1, SLOT_END=7, SLOT_BASE=7`。目標はスロット 7（60 分） |
| 目標の判定 | 受け入れた数 1。目標 − モデル平均 = +4.39 Pa（見込み 3.5 Pa。目標値を決めた予報と丸め誤差の分だけ違う） |
| **mdet の修正量** | **最下層の QV だけが減った**。目標地点で −0.02413 g/kg。増える向きの修正はない。2 層目より上は 0 |
| 修正の広がり | 目標から **73 km 以内で一定（−0.02413 g/kg）、その外は 0** |
| 他の変数 | DENS（最大 1.7e-5）と RHOT（最大 0.005）が QV の変化に合わせて変わった。風・水物質・陸面は 0 |
| 制御前の mdet | `gues/mdet/` に残っていた |
| **0001〜0020** | **最下層の QV が約 0.017 g/kg 変わった**（DENS 1.1e-5、RHOT 0.0034 も） |
| step 7 の mdet と step 3（比較用）の 60 分の差 | MOMZ 0.075、RHOT 0.196、QV 8.2e-4。M1a の雑音（0.044、0.087、4.7e-4）の 1.7〜2.3 倍 |
| 目標地点の 60 分の地上気圧（mdet） | 999.978 → 999.977 hPa。目標（高くする）には近づいていない |
| `nobs` | 今回もすべて 0。制御がかかったのに 0 なので、**この出力は使えない**（2 回目の「どの格子点にも使われていない」も根拠にならない） |

**修正が「円盤」になる理由:** LETKC は距離による重みを意図的に外している（`letkc/letkf_tools.f90` 2024 行
`nrloc = nrloc * 1.0d0  ! No relaxing the impact based on distance in LETKC  YSaw 20241120`）。
元の LETKF では、ここで距離に応じたガウス型の重みを掛ける。LETKC では `HORI_LOCAL` は「影響の強さの広がり」ではなく
「影響が届く範囲の境目（`HORI_LOCAL` × 3.65）」だけを決める。

**0001〜0020 も変わる理由:** LETKC は、制御する層（最下層、`clev = 1`）で修正が減る向きなら、member の解析値もそのまま残す
（`letkc/letkf_tools.f90` 649–690 行。member を元に戻すのは、それ以外の層と、修正が増える向きの場合だけ）。
当初の合格条件「0001〜0020 は変わっていない」は、この作りを知らずに書いたもの。

**どちらの変更が効いたか:** 2 回目（`LTIMESLOT=3600`、高さ 0 m）でも目標は受け入れられていた（10 分の値との差 +3.29 Pa）ので、
時刻の食い違いだけでは修正がゼロになる理由にならない。高さ 0 m が原因だった可能性が高いが、確かめてはいない。

**制御の物理的な効果:** 最下層の水蒸気を 73 km 以内で一様に 0.024 g/kg 減らしても、1 時間後の目標地点の気圧はほとんど変わらなかった。
0 分の最下層の QV と 60 分の目標地点の気圧の相関が −0.02 と弱いため。制御指標を決めるとき（8.1 節）に考える。

## M1b の判定（2026-09-27）

3 回目の結果で **M1b は合格**（ユーザーと合意）。合格条件を LETKC の実際の作りに合わせて改めた:
- 「0001〜0020 は変わっていない」を外した（制御する層で減る向きなら member の解析値も残す作り）。
- 修正は `HORI_LOCAL` × 3.65 以内で一様な「円盤」になる（距離による重みを外している）ことを前提にした。
- step 7 の変化は M1a の雑音の 1.7〜2.3 倍で、雑音より大きい。

これで M1（Phase 6）は完了。

## 後始末（2026-09-27）

診断用の設定を元に戻した: `config.nml.letkc` の `LOG_LEVEL` を 3 → 1、`config.cycle` の `NOBS_OUT` を 1 → 0。
`LTIMESLOT=600` と「目標の高さは最下層」は残す。

## 目標の高さ 0 m が原因だったかの確認（2026-09-27 準備）

M1b の 1・2 回目（`LTIMESLOT=3600`、高さ 0 m）では制御がかからず、3 回目（`LTIMESLOT=600`、高さ 37.5 m）でかかった。
2 つを同時に変えたので、どちらが効いたかを確かめる（ユーザーの依頼）。

- **変えるのは高さだけ:** `LTIMESLOT=600` のまま、目標を `controltarget_ctltest`（1000.03 hPa・誤差 0.01 hPa・**高さ 0 m**）に戻した。
  この目標値は、60 分の目標地点の地上気圧の 20 member 平均（換算なし、約 999.995 hPa）より約 3.5 Pa 高くなるように決めたもの。
- 制御がかかれば、高さ 0 m は問題なく、1・2 回目の原因は時刻の食い違い（10 分の値と比べていた）。
  かからなければ、高さ 0 m が原因。
- 診断用の設定は戻してある（`LOG_LEVEL=1`、`NOBS_OUT=0`）。判定には、ログの統計（目標とモデル平均の差）と mdet の修正量を使う。
- STIME の初期値を取り込み直した（22 member すべて md5 一致）。
