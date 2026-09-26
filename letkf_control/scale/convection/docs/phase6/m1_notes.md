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
