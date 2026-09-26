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
