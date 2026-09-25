# 制御シミュレーションの処理フロー（`case_tc`）

この文書は、`letkf_control/scale/run` にある現行設定をもとに、
理想化熱帯低気圧ケース（`case_tc`）で実行している制御シミュレーションの
役割とデータの流れをまとめたものです。

## 現行の主な設定

| 項目 | 現行値 | 設定箇所 |
| --- | --- | --- |
| 実験ケース | `case_tc` | `config.*` は `config/case_tc/` へのシンボリックリンク |
| 結果出力先 | `/work/gv42/v42013/20260603_enkc/result/case_tc` | `config.main.Wisteria` の `OUTDIR` |
| アンサンブル数 | 100 | `MEMBER=100` |
| 決定論メンバー | 有効 | `DET_RUN=1` |
| 決定論メンバーの更新 | LETKC のみで更新 | `DET_RUN_UPDATE=2` |
| 境界条件 | なし（理想化実験） | `BDY_FORMAT=5`、`SOUNDING=.../tropicalcyclone.txt` |
| 同化窓・サイクル間隔 | 0–3600秒・3600秒 | `WINDOW_S=0`、`WINDOW_E=3600`、`LCYCLE=3600` |
| サイクル期間 | 2000-01-01 00:00:00〜2000-01-10 00:00:00 | `config/case_tc/config.cycle` |
| 水平並列 | 8 × 4 = 32 MPIプロセス / SCALE実行 | `SCALE_NP_X=8`、`SCALE_NP_Y=4` |
| ノード内並列 | 4 MPIプロセス、各12 OpenMPスレッド | `PPN=4`、`THREADS=12` |
| 同化用観測 | `test_obs_3d_intv2_xyp.dat` | `OBSIN` |

## 全体のデータフロー

```text
設定・実行スクリプト
  config.main / config.cycle / config.nml.*
  cycle_run.sh
        |
        |  一時実行環境を作成し、実行ファイル・設定・観測を配置
        v
cycle.sh（各同化時刻で実行）
        |
        +--> SCALE 前処理・初期化
        |      scale-rm_pp_ens / scale-rm_init_ens
        |
        +--> 100メンバー + 決定論メンバーのSCALE予報
        |      scale-rm_ens
        |      出力: <OUTDIR>/<時刻>/hist/, gues/, log/
        |
        +--> LETKC（決定論メンバーを更新）
        |      letkc
        |      出力: <OUTDIR>/<時刻>/anal/
        |
        +--> 観測作成・観測演算子
        |      obsmake -> obsope（または PAWR decoder）
        |
        +--> LETKF（アンサンブルを更新）
        |      letkf
        |      出力: <OUTDIR>/<次時刻>/anal/
        |
        +--> 次サイクルの初期値として anal を gues に引き継ぐ
        v
次の同化時刻
```

`DET_RUN_UPDATE=2` のとき、`src/func_cycle_static.sh` で定義される実行順は
次の11ステップです。

1. `scale-rm_pp_ens`：SCALE前処理
2. `scale-rm_init_ens`：初期値・境界用の初期化
3. `scale-rm_ens`：アンサンブル予報
4. `letkc`：決定論メンバーの解析更新
5. `scale-rm_pp_ens`：更新後の決定論メンバー用前処理
6. `scale-rm_init_ens`：更新後の決定論メンバー用初期化
7. `scale-rm_ens`：更新後の予報
8. `obsmake`：モデル履歴から観測相当量を作成
9. `obsope`（または PAWR decoder）：観測演算子／レーダ復号
10. `letkf`：アンサンブル解析
11. `efso`：有効化時のみ実行する感度診断

## 各エントリポイント

### 同化サイクル: `cycle_run.sh`

`cycle_run.sh` が外側の投入スクリプトです。設定を読み込み、実行用の一時
ディレクトリを初期化して、実行ファイル・`config.nml.*`・観測入力を配置し、
Wisteria のPJMジョブとして `cycle.sh` を投入します。

`cycle.sh` は `STIME` から `ETIME` まで `LCYCLE` 間隔でループします。各時刻で
解析時刻 `atime = time + LCYCLE` を定め、上記の処理を実行します。解析出力は、
次サイクルの第一推定（`gues`）としてコピー／参照されます。

### 予報のみ: `fcst_run.sh`

`fcst_run.sh` は同化を行わず、解析または指定メンバーから予報を伸ばすための
入口です。`fcst.sh` は以下を順に実行します。

1. `scale-rm_pp_ens`
2. `scale-rm_init_ens`
3. `scale-rm_ens`

現行の `config/case_tc/config.fcst` では、開始時刻は
`2000-01-01 00:00:00`、予報長・出力間隔はいずれも10,800秒です。

### 観測入力と観測作成

`config.main.Wisteria` の `OBSIN` は
`config/case_tc/make_obsin/test_obs_3d_intv2_xyp.dat` を指定しています。
`cycle_run.sh` はこれを一時領域の `obsin/obsin.dat` にコピーします。

サイクル中の `obsmake` はモデルの履歴出力から観測に対応する量を作り、続く
`obsope` が観測演算子として利用します。観測結果は `OUTDIR/obs/` および各時刻の
観測関連出力に保存されます。`config/case_tc/make_obsin/` は、この観測入力を作る
Fortranプログラム群です。`controltarget/cntltargetmakein_p` は NetCDF 履歴を読み、
制御対象用のバイナリファイル（例: `controltarget_10`）を出力します。

### SNO による後処理: `sno_merge.sh`

`sno_merge.sh` は同化計算そのものとは独立した後処理です。SNOを一括ジョブとして
投入し、`OUTDIR/<時刻>/<種別>/<メンバー>/history` などの分割SCALE出力を、指定した
プロセス分割数で再構成します。現行値は次のとおりです。

- 対象時刻: 2000-01-07 00:00:00〜2000-01-09 23:00:00（1時間間隔）
- 対象種別: `hist`
- 対象メンバー: `mdet` と `mean`
- 出力分割: 8 × 4 = 32

## ディレクトリと設定の対応

| パス | 内容 |
| --- | --- |
| `config.main` | `config/case_tc/config.main.Wisteria` へのリンク。実行環境・出力先・並列数・同化窓などの共通設定。 |
| `config.cycle` | サイクル実行期間、出力量、インフレーション等の設定。 |
| `config.fcst` | 予報実行の開始時刻、対象メンバー、予報長の設定。 |
| `config.nml.letkc` | LETKCのNamelistテンプレート。QCを実質無効化する `GROSS_ERROR=1000000.0D0` を含む。 |
| `config.nml.letkf` | アンサンブルLETKFのNamelistテンプレート。 |
| `config.nml.obsmake` | モデル履歴を用いた観測作成のNamelistテンプレート。 |
| `src/cycle.sh` | 同化サイクル本体。各実行ファイルを指定順にMPI起動する。 |
| `src/fcst.sh` | 同化なし予報の本体。 |
| `src/func_cycle_static.sh` | ステップ順、設定ファイル生成、入出力・ステージング規則を定義する。 |
| `sno_merge.sh` | 出力をSNOで再構成する後処理。 |

## 実行前に確認すべき点

1. `config.main.Wisteria` の `OUTDIR`、`OBSIN`、`SOUNDING` が目的の実験を指していること。
2. `config/case_tc/config.cycle` の開始・終了時刻、`LCYCLE`、同化窓が整合していること。
3. `MEMBER`、`SCALE_NP_X/Y`、`PPN`、`THREADS` から算出される必要ノード数を確保できること。
4. `DET_RUN_UPDATE=2` では LETKC と LETKF の両方がサイクルに含まれること。
5. `DISK_MODE=0` では中間データのステージングを行わず、共有ファイルシステムを直接使うこと。
6. `sno_merge.sh` の時刻範囲・対象メンバーは固定値なので、別の出力を変換する場合は明示的に変更すること。
