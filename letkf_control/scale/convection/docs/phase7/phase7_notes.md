# Phase 7 — obsmake / LETKF

## 方針（2026-09-27 決定）

- M1 と同じく 2 段階に分ける。
  - **7a（obsmake）**: step 1–8。2 km 格子用の OBSIN から、mdet の 60 分の予報で観測 `$OUTDIR/obs/obs_20000101010000.dat` を作る。
  - **7b（LETKF）**: step 1–10。0001–0020 の analysis を作る。
- **制御なし**（`controltarget_nocontrol`、地上気圧 10 hPa）で行う。Phase 7 は obsmake・LETKF の配管の確認なので、制御と切り分ける。
- MEMBER = 20、regular-o（large-o）。

## 準備したもの（2026-09-27）

### controltarget

`make_controltarget.py nocontrol --install` で `$OUTDIR/obs/controltarget` を制御なしに戻した（M1a と同じ中身であることを `cmp` で確認）。

### OBSIN

`convection/make_obsin/obsin/make_obsin.py` で作った `make_obsin/obsin/obsin_uvt_intv4`。

| 項目 | 値 |
| --- | --- |
| 要素 | U, V, T（2819, 2820, 3073） |
| 水平 | 4 格子おき（8 km）。全体の格子番号 1, 5, …, 117 の 30 × 30 点 |
| 鉛直 | 2 層おき（モデルの層 1, 3, …, 63 の 32 層）。高さは気圧で指定し、その格子点・その層の 0 分の気圧（STIME の mdet の history）を使う |
| 個数 | 30 × 30 × 32 × 3 = **86,400**（case_tc は 144,000） |
| 観測値・誤差 | 仮の値 10.0・1.0（obsmake が上書きする） |
| 種類・dif | 1.0（ADPUPA）・0 s（スロット 7 = 60 分） |
| 形式 | case_tc の `obsmakein_p.f90` と同じ（40 バイト、リトルエンディアン、real(4) × 8） |

読み戻した結果: 経度 −1.070〜1.016°、気圧 32.5〜996.2 hPa。緯度は 900 通り（この地図投影では緯度が x にもよる。モデル自身の経度・緯度を使っているので問題ない）。

`config.main.Wisteria` の `OBSIN` をこのファイルにした（それまでは case_tc 用を仮に置いていた）。
`cycle_run.sh` 91 行がジョブの開始時に `$TMP/obsin/obsin.dat` にコピーし、obsmake はこれを読む。
`config.obsmake` は `obsmake_run.sh` 用で cycle では使わないので、変えていない。

### 設定の変更

| ファイル | 変更 | 理由 |
| --- | --- | --- |
| `config.nml.obsmake` | `OBSERR_Q` 0.1 → **0.001** | 単位は kg/kg（`common/common_nml.f90` の既定値は 0.001）。obsmake はこの誤差で観測にノイズを足し、Q を 0 以上に切り詰める（`obs/obsope_tools.f90` 711–716 行）。下層の Q は約 0.015 kg/kg なので、0.1 では観測値が失われ正の偏りも入る。今回の OBSIN に Q はないが、後で入れるときのために直した |
| `config.nml.letkf` | `HORI_LOCAL` 150 km → **20 km** | LETKF の打ち切りは `HORI_LOCAL` × 3.65 なので、150 km では約 550 km となり 240 km の領域全体が 1 つの局所領域になる。20 member では偶然の相関が入りやすい。LETKC と同じ 20 km（約 73 km で打ち切り）から始める |

観測誤差は OBSIN の 6 番目の値ではなく、obsmake の `OBSERR_*`（U, V 0.1 m/s、T 0.1 K）で上書きされ、`obs_<t>.dat` に書かれる。LETKF はその値を使う。

### 時刻の扱い（確認済み）

- obsmake の `SLOT_TINTERVAL` には `CYCLEFOUT`（= `FCSTOUT` = 600）が入る（`src/func_cycle_static.sh` 1342・1876 行）。
  `obstime` で `SLOT_START=1, SLOT_END=7, SLOT_BASE=7` となり、`dif = 0` の観測はスロット 7（history の 7 番目 = 60 分）で計算される。
- step 8 の後、`$TMP/obsin/obsin.dat.out` が `$OBS/obs_<atime>.dat` にコピーされ（`src/cycle.sh` 631 行）、step 10 の LETKF がそれを読む（`func_cycle_static.sh` 866 行）。

## 実行の手順

### 0. STIME の初期値を取り込み直す（毎回）

前の実行（M1b・確認用 LETKC）で LETKC が STIME の `anal/` を書き直しているので、取り込み直す。

```bash
rm -rf /work/gv42/v42013/20260923_enkc_convection/result/20000101000000/anal /work/gv42/v42013/20260923_enkc_convection/result/20000101000000/gues
cd /work/02/gv42/v42013/scale-letkc/letkf_control/scale/convection/init && ./import_rep_asakura.sh
```

### 7a（obsmake）

```bash
cd /work/02/gv42/v42013/scale-letkc/letkf_control/scale/convection
./cycle_run.sh 20000101000000 20000101000000 1 8 static 00:30:00
```

確認すること:
1. ログに `stop`・`cannot stat` がない。
2. `$OUTDIR/obs/obs_20000101010000.dat` があり、レコード数が 86,400（undef を落とすなら、それ以下で理由が説明できる）。
3. obsmake のログで、観測がスロット 7 に入っている。
4. 観測値が、mdet の 60 分の history を観測地点で補間した値と、誤差（0.1）程度の範囲で一致する（数点を照合）。

### 7b（LETKF）

0 の取り込み直しをしてから:

```bash
./cycle_run.sh 20000101000000 20000101000000 1 10 static 00:30:00
```

- **途中の step（ISTEP = 9, 10）からは再開しない。** `ISTEP > 3` の準備（`src/func_cycle_static.sh` 1160–1166 行）は
  全 member の `gues/` を `anal/` に戻す作りだが、`gues/` には mdet しか残らないので失敗する。毎回 1 から流す。

確認すること:
1. LETKF が異常終了していない（`stop` なし）。
2. `20000101010000/anal/0001–0020` が step 10 の時刻に書き換わっている。
3. `anal/mean − gues/mean`（60 分）の増分がゼロでなく、観測のある場所のまわり（約 73 km 以内）に収まっている。
4. LETKF のログの OBSERVATIONAL DEPARTURE STATISTICS で、O−A の RMSE が O−B より小さい
   （LETKF の解析時刻は 60 分なので、LETKC と違いこの統計は意味がある）。
5. analysis のばらつきが極端に潰れていない（`INFL_MUL = 1.45`、`RELAX_ALPHA = 0.8` のまま）。
6. mdet は LETKF で変わっていない（`DET_RUN_UPDATE = 2`）。
7. 各 step の時間（Phase 8 の `TIME_LIMIT` とノード時間の見積もりに使う）。

## 未確認のこと

- LETKF の局所化の距離は経度・緯度から計算していて、二重周期の境界をまたぐ観測は効かない可能性がある（コードでは未確認）。7b の増分の分布で確かめる。

## 記録

（7a・7b の結果をここに書く）
