# LETKC の改造の作業計画：土壌水分による降水の制御を、LETKC の正規の流れに乗せる（2026-11-07）

notes.md 1.3 の設定（毎時の介入、T_c = 1 時間、Y = t + 45〜75 分の積算、y* = 0.8 Ȳ、σ_R = σ_Y、土壌水分は同化の外でばらつきは足さない）を、
LETKC の正規の流れ（controltarget → 観測演算子 → 品質管理 → 局所 ETKF → 書き出し・診断）の上で実装する。

最初の実装（`letkc/soil_control.f90`、notes.md 3.9）は、この流れを全部迂回していた。
ユーザーの判断（2026-11-07）で、次の形に作り直す:

- 制御目標は controltarget（疑似観測のファイル）で与える
- 局所化半径の機能を使えるようにする（汎用性のため）
- 目標の種類は後で増やすので、種類を足しやすい作りにする
- 観測ファイルの形式・品質管理・診断の出力（obsdep など）を残す
- **LETKF の仕組みをそのまま使う**（状態変数の読み書き・観測演算子・局所 ETKF・変数の局所化で制御する変数を選ぶ、という Sawada の LETKC の作り方に揃える）。
  迂回のモジュール（`soil_control.f90`）は残さない

作業は下のタスクに分け、1 つずつ進める（トークンの残りに応じて区切る）。各タスクの終わりに、この文書の「状況」と「作業の記録」を更新する。

## 0. 今の LETKC の流れ（letkc/letkf.f90）

| 段階 | ルーチン | 今の動き | 作り直しで変えること |
| --- | --- | --- | --- |
| ① 目標を読む | `read_obs_all_mpi` | controltarget（8 個の real(4) のレコード: 要素番号・経度・緯度・高さ・値・誤差・種類・dif）を読む | 新しい要素番号を受け付ける（タスク 1） |
| ② 観測演算子 | `obsope_cal`（`obs/obsope_tools.f90`。LETKF・obsmake と共有、`../common` でコンパイルしたものを LETKC にもリンクしている） | 観測 1 つを 1 つの subdomain・1 つのスロットに割り当て、そのスロットの history（`read_ens_history_iter`）から `Trans_XtoY` で点の値を出す | LETKC 用の観測演算子を `letkc/` に分け、領域・時間で積算する種類を足す（タスク 2） |
| ③ 品質管理 | `set_letkf_obs`（`letkc/letkf_obs.f90`） | gross error、「目標 − 予報 < 0 は捨てる」（地上気圧の制御用。513 行） | 捨てる規則を要素ごとに選べるようにする。相対目標・相対誤差（タスク 1） |
| ④ 第一推定 | `read_ens_mpi` | restart から大気の 11 変数（`state_trans` で変換） | `LAND_WATER` の層を状態変数に加える（タスク 3） |
| ⑤ 修正量 | `das_letkf`（`letkc/letkf_tools.f90`） | 局所 ETKF。member は ETKF の変換（平均の移動 + ばらつきの変換）、mdet は自分の差（y* − H(x_mdet)）とゲインで更新（`transmd`、476〜486 行）。そのあと、制御する変数は変数の局所化で QV だけ（643 行あたり、`var_local(6,4) = 1`）、最下層 3 層（`clev`）、減らす向きだけ（`force_check`）、λ の閾値（`control_lamda`）。すべてコードに固定 | 制御する変数・層・向き・範囲・λ を設定（namelist）で選べるようにする（タスク 3） |
| ⑥ 書き出し | `write_ens_mpi` | 解析の全変数（mean・member・mdet） | `LAND_WATER` の層も書き出す（タスク 3） |

## 1. 設計の決めごと

### controltarget の新しい要素（タスク 1）

- レコードの形式は今のまま（8 個の real(4)）。新しい要素番号を足す
  - 例: `id_ctl_areaacc = 19001`（2 次元の history の変数を、長方形の領域で平均し、時間の窓で積算する）。既存（`common_obs_scale.f90` 49〜73 行）と重ならない値にする
- レコードの各欄の使い方（この要素）
  - 経度・緯度: 領域の中心（LETKC は `phys2ij` で格子に直し、局所化の距離もここから測る）
  - 高さ: 使わない（0）。地上の観測と同じ扱い
  - 値: 目標値。相対目標のときは比（0.8）
  - 誤差: 疑似観測の誤差。相対誤差のときは σ_Y に対する係数（1.0）
  - 種類: 目標の定義の番号（下の namelist の表の行）
  - dif: 窓の中心の時刻。既存の観測と同じく SLOT_BASE の時刻（予報の開始 t + LCYCLE）からの秒。予報 t + 45〜75 分の窓なら 0（当初 +3600 と書いたが 1 時間ずれるので訂正、2026-11-07、タスク 2 から）
- 種類ごとの定義は namelist の表（`&PARAM_CTLTARGET`、配列）
  - 変数名（`PREC`）、領域の半幅 x・y [m]（10 km・10 km）、窓の半幅 [s]（900）、積算か平均か、相対目標か、相対誤差か、「負の差を捨てる」か
  - 新しい種類（領域の最大、点の値、ほかの変数）は、表の列と演算子の分岐（`select case`）を 1 つ足せば増やせる作りにする
- 相対目標・相対誤差は、全 member の H(x) が出た後・QC の前に、Ȳ・σ_Y から y*・σ_R を決めて obs の値・誤差に入れる

### 観測演算子（タスク 2）

- LETKC 用の観測演算子のモジュールを `letkc/` に作る（`obs/obsope_tools.f90` を写して `common_letkc` でコンパイルする）。
  LETKF・obsmake の `obs/` は変えない。今の「`../common` でコンパイルした obsope_tools.o を `common_letkc` とリンクする」ねじれも、これで解消する
- `obsope_cal` に「領域・時間で積算する要素」の分岐を足す
  - 今の作りは「観測 1 つ = 1 つの subdomain・1 つのスロット」。この要素は、領域が複数の subdomain、窓が複数のスロットにまたがるので、
    各プロセスが自分の subdomain・各スロットの部分和を出し、MPI（`MPI_COMM_d`）で集めて、その観測を受け持つプロセスに置く
  - history の読み方は、下の「history とスロット」の決め方による
- 要素の値は obsda に入り、そのあと ③〜⑤ と obsdep などの診断の出力はふつうの観測と同じ道を通る

### history とスロット（**案 A に決定**、2026-11-07、ユーザー）

LETKF の仕組み（スロット = history の k 番目の時刻）をそのまま使うには、PREC の history の時刻の並びがスロットと合っている必要がある。

- 案 A: history 全体を 5 分ごと（`FCSTOUT = LTIMESLOT = 300`）にし、PREC だけ時間平均（`TINTERVAL = 300`・`TAVERAGE`）。
  スロットの読み込み（`read_ens_history_iter`）をそのまま使える。history は 1 cycle あたり約 2 倍（member の history は LETKF の後に消すので一時的）。
  LETKF の観測の時間の割り当ても 5 分刻みになる（観測は毎時の 1 時刻だけなので、結果は変わらない見込み）。notes.md 1.3 の「ほかの変数は 10 分ごとの瞬間値のまま」を変えることになる
- （採らない）案 B: 今のまま（ほかの変数は 10 分、PREC だけ 5 分）。この要素の演算子だけ、history の PREC を自分の時刻の並びで直接読む。スロットの仕組みからは外れる
- LETKC のスロットの範囲は、窓の終わり（t + 75 分）まで要る。LETKC の設定ファイルの `SLOT_END` を、予報の長さ（`SENS_CYCLEFLEN`）から作る（LETKF の設定は変えない）

### 状態変数と修正の制約（タスク 3）

- `LAND_WATER` の上の層（1・2 層）を、2 次元の変数として状態（`v2d`）に加える（`common_scale.f90` の `nv2d`・`v2d_name`、`read_restart`・`write_restart` で lz の層を切り出す・戻す）
- 制御する変数・層・向き・範囲・λ を `&PARAM_LETKC_CONTROL`（仮）で与える
  - 例: 修正する変数 = `LAND_WATER_1`・`LAND_WATER_2`、向き = 増やすだけ、範囲 = 0〜0.5、λ = 0
  - 今の QV の設定（QV・最下層 3 層・減らすだけ）も、この設定で再現できるようにする（既定値を今の動きに合わせる）
- 変数の局所化（`var_local`）の制御の行も、この設定から作る
- member・mdet の更新は、今の LETKC のまま（member は ETKF の変換、mdet は自分の差とゲイン）。「mdet の増分を member にそのまま足す」という最初の実装の扱いはやめる
  - 注意: この形では、mdet の修正量は y* − H(x_mdet)（mdet 自身の予報との差）で決まる。最初の実装（y* − Ȳ）とは違う。
    また member は ETKF でばらつきも変換される（目標を「情報」として扱うので、ばらつきが縮む）。これが Sawada の LETKC の作り

### 局所化

- 水平の局所化は今の `HORI_LOCAL` をそのまま使う（距離は目標領域の中心から）。今回の実験は `HORI_LOCAL = 1.0D6`（領域全体）を予定
- 今の LETKC は距離による重みを外している（`letkf_tools.f90` 2024 行。`HORI_LOCAL × 3.65` 以内は一様）。これは変えない

## 2. タスク

| # | 中身 | 終わりの形 | 状況 |
| --- | --- | --- | --- |
| 1 | controltarget の新しい要素、`&PARAM_CTLTARGET`、相対目標・相対誤差、QC の規則を要素ごとに。`make_controltarget.py` に新しい目標 `mpc_areaprec` | ビルドが通る。既存の要素の動きは変わらない | 済み（2026-11-07。ビルドのみ。実行は未確認） |
| 2 | LETKC 用の観測演算子のモジュールを `letkc/` に分け、領域・時間で積算する要素を足す（案 A: history 全体 5 分、スロットで読む）。LETKC の `SLOT_END` を予報の長さに合わせる | ビルドが通る。obsdep にこの要素が出る作り | 済み（2026-11-07。ビルドのみ。実行は未確認） |
| 3 | `LAND_WATER` を状態変数に加える。`&PARAM_LETKC_CONTROL`（制御する変数・層・向き・範囲・λ、変数の局所化） | ビルドが通る。QV の設定の既定値で今と同じ動き | 済み（2026-11-07。ビルドのみ。実行は未確認） |
| 4 | cycle との接続（`submit.sh` を controltarget を置く形に）、`soil_control.f90` と迂回のモードを消す、2 member・1 cycle の試験、Python での検算（ETKF の式で） | 試験が通り、Y・修正量が検算と合う | 済み（2026-11-07。2 member・1 cycle の試験が通り、Y・y*・σ_R・修正量が検算と合った） |

各タスクで変えたファイル・確かめたこと・決めたことは、この文書の末尾に追記する。実験の結果は notes.md に書く。

## 3. 作業の記録

### タスク 1（2026-11-07）

`letkc/` で `SCALE_SYS=FX700 make letkc` が通ることを確かめた（`common_letkc/` を make したあと、`letkc/` の .o・.mod を消して作り直し）。
ジョブは流していないので、実行しての確認はまだ。`soil_control.f90` は触っていない。

**変えたファイル**

| ファイル | 変更 |
| --- | --- |
| `common_letkc/common_nml.f90` | `nid_obs` 16 → 17。`&PARAM_CTLTARGET` の変数と `read_nml_ctltarget`。`&PARAM_LETKF_VAR_LOCAL` に `VAR_LOCAL_CTL`（既定 0） |
| `common_letkc/common_obs_scale.f90` | `id_ctl_areaacc = 19001`。`elem_uid`・`obelmlist`（`'CTA'`）・`uid_obs`（17）。`nid_obs_varlocal` 8 → 9、`obelmlist_varlocal`（`'CTL'`）・`uid_obs_varlocal`（9）。関数 `is_ctl_obs` |
| `common_letkc/common_mpi_scale.f90` | `set_scalelib` の LETKF の分岐で `read_nml_ctltarget` を呼ぶ |
| `letkc/letkf_obs.f90` | `set_letkf_obs`: 相対目標・相対誤差、その値を全プロセスに配る処理、QC の要素ごとの規則 |
| `letkc/letkf_tools.f90` | `var_local(:,9) = VAR_LOCAL_CTL`。鉛直の局所化で制御目標は `nd_v = 0` |
| `make_obsin/controltarget/make_controltarget.py` | 目標 `mpc_areaprec`、格子点の間の経度・緯度の内挿（`lonlat_at`）、`--hist` |
| `make_obsin/controltarget/controltarget_mpc_areaprec` | 作った controltarget（下） |

**決めたこと**

- 要素番号 `id_ctl_areaacc = 19001`（既存の地上の番号 14593・19999・99991〜99993 と重ならない）。
  種類を足すときは `id_ctl_*` を足し、`elem_uid`・`obelmlist`・`uid_obs`・`uid_obs_varlocal`・`is_ctl_obs` と `nid_obs` を直す
- controltarget の 7 番目の欄（観測の種類 `typ`、1〜24）を `&PARAM_CTLTARGET` の表の行番号にした。
  `typ` は `USE_OBS`・`HORI_LOCAL`・`VERT_LOCAL` の添字でもあるので、行ごとに局所化も変えられる（22 = PHARAD は鉛直の局所化が z になるので避ける）
- `&PARAM_CTLTARGET` の列（配列の長さ `nobtype`）

  | 変数 | 既定 | 意味 |
  | --- | --- | --- |
  | `CTL_VAR` | `''` | history の変数名。`''` の行は使わない（その `typ` の目標は `iqc_otype` で捨てる） |
  | `CTL_HALF_X`・`CTL_HALF_Y` | 0 | 領域の半幅 [m] |
  | `CTL_HALF_T` | 0 | 窓の半幅 [s]（窓の中心は dif） |
  | `CTL_AREA_OP` | `'MEAN'` | 領域の演算（今は `'MEAN'` だけ。最大などは case を足す） |
  | `CTL_TIME_OP` | `'SUM'` | 時間の演算: `'SUM'`（積算）・`'MEAN'`（平均） |
  | `CTL_REL_TARGET` | `.false.` | y* = 値 × Ȳ |
  | `CTL_REL_ERROR` | `.false.` | σ_R = 誤差 × σ_Y |
  | `CTL_REJECT_NEGDEP` | `.false.` | y* − Ȳ < 0 を捨てる |

  読み込み時に、使う行の `CTL_AREA_OP`・`CTL_TIME_OP` を `select case` で確かめ、知らない値なら止める。
  今回の実験の設定（タスク 4 で LETKC の設定ファイルに書く）:

  ```
  &PARAM_CTLTARGET
   CTL_VAR(1) = 'PREC', CTL_HALF_X(1) = 10.0D3, CTL_HALF_Y(1) = 10.0D3, CTL_HALF_T(1) = 900.0D0,
   CTL_AREA_OP(1) = 'MEAN', CTL_TIME_OP(1) = 'SUM',
   CTL_REL_TARGET(1) = .true., CTL_REL_ERROR(1) = .true., CTL_REJECT_NEGDEP(1) = .false.,
  /
  ```
- 相対目標・相対誤差は `set_letkf_obs` の departure のループの中、レーダーの処理の後・平均と departure の計算の前で入れる。
  Ȳ・σ_Y は member（`obsda%ensval(1:MEMBER,n)`）の平均と標準偏差（分母 MEMBER − 1）。mdet は含めない。
  mdet の departure は y* − H(x_mdet)（y* は member の Ȳ から決めたもの）。σ_R ≤ 0（ばらつきがない）なら `iqc_obs_bad`
- 決めた y*・σ_R は `obs(iof)%dat`・`%err` を書き換えて入れる。`obs(:)` は全プロセスが同じものを持ち、
  局所化の重み（`letkf_tools.f90` の `nrdiag`）と obsdep の出力は、観測の持ち主でないプロセスでも `obs(:)%dat`・`%err` を読むので、
  ループの後に `MPI_ALLREDUCE`（`MPI_COMM_d`）で全 subdomain に配る。
  相対の処理の前に QC で落ちた目標（今は H(x) がないので全部）は、`obs(:)%dat` が比のまま obsdep に出る
- QC: 新しい要素（`case (id_ctl_areaacc)`）は gross error（`GROSS_ERROR × σ_R`）を残し、負の差の規則は `CTL_REJECT_NEGDEP(typ)` に従う。
  既存の要素（`case default`）の「負の差を捨てる」はそのまま
- 鉛直の局所化: 制御目標は高さを使わないので `nd_v = 0`（`letkf_tools.f90`。高さ 0 で `LOG(lev)` を取らないため）
- 変数の局所化: 新しい列 9（`VAR_LOCAL_CTL`、既定 0 = どの変数も直さない）。既定がすべて 0 なので、変数のまとめ方（`var_local_n2nc`）も既存の動きも変わらない。
  H08 の `uid_obs_varlocal` は 9 → 10（もともと `nid_obs_varlocal` の外で、使っていない）
- `mpc_areaprec`: 要素 19001、経度 −0.359711・緯度 0.000000（領域の中心 x = 80 km・y = 120 km。格子点の間なので、まわりの 4 点から双線形に内挿）、
  高さ 0、値 0.8、誤差 1.0、種類 1、dif 0（はじめ +3600 で作ったが、dif は SLOT_BASE = t + 60 分からの秒なので 0 に直した。`slotcheck` の「dif = 0 → スロット 7（60 分）」と同じ基準）。
  スクリプトの既定の `HIST`（`result/20000101000000/hist/mdet`）は今はないので、`--hist /work/gv42/v42013/20260923_enkc_convection/result_m80/20000131000000/hist/mdet` で作った（格子は全実験で同じ。`ctltest` を作り直して前のファイルと同じになることを確かめた）

**タスク 2 への申し送り（obsda の作り）**

- `obsda`（`letkf_obs.f90` の `type(obs_da_value)`）: 観測 1 つにつき 1 要素。`set(n)`・`idx(n)` が `obs(set)%…(idx)` を指す。
  `ensval(im,n)` が H(x)（im = 1〜MEMBER が member、`mmdetobs` が mdet）、`qc(n)`、`val(n)`（departure の計算に使う）
- `obsope_cal` は、観測を `obs%rank`（`ri`・`rj` の subdomain）と dif のスロットに割り当て、そのプロセスの `obsda` に H(x) を入れる。
  `obs_da_value_allreduce` が `MPI_COMM_e` で member の `ensval` を集めるので、`set_letkf_obs` の時点では、同じ subdomain の全プロセスが全 member の H(x) を持つ。
  新しい要素も、H(x)（領域・窓の積算）を持ち主のプロセスの `obsda%ensval` に入れれば、相対目標・QC・局所 ETKF・obsdep はそのまま通る
- 今は `Trans_XtoY` の `case default` で `iqc_otype` になる（新しい要素は QC で落ちる）
- `set_letkf_obs` の後で subdomain の間に渡るのは `set`・`idx`・`val`・`ensval`・`qc` だけ。`dat`・`err` は各プロセスの `obs(:)` から読む（上の配る処理はこのため）
- `obs/obsope_tools.o` は `../common` でコンパイルされたまま `common_letkc` とリンクしている。`nid_obs` が 16 と 17 で食い違うが、
  `obsope_tools.f90` は `nid_obs` を使っておらず、module の変数は 1 つずつ別の記号（`nm` で確認）なので、リンクは今のところ問題ない。タスク 2 で `letkc/` に写せば解消する
- `CTL_TIME_OP = 'SUM'` の積算は「値 × 時間」のつもり（PREC [kg m⁻² s⁻¹] → [mm]）。スロットの時間幅の掛け方（5 分の時間平均 × 300 s の和）はタスク 2 で決めて書く
- gross error は σ_R = σ_Y で効く（|y* − Ȳ| = 0.2 Ȳ > `GROSS_ERROR` × σ_Y で捨てる）。今の `config.nml.letkc` は `GROSS_ERROR = 1.0D6`（QC なし）なので落ちない見込み。
  タスク 4 の試験で、ログの `[Info] LETKC control target`（LOG_LEVEL ≥ 1、Ȳ・σ_Y・y*・σ_R）を見て確かめる

### タスク 2（2026-11-07）

`common_letkc/` を make したあと、`letkc/` で `SCALE_SYS=FX700 make letkc` が通ることを確かめた（`letkc` に `obsope_tools_ctl` の記号が入っている）。
`efso` は作っていない（Makefile は同じ形に直した）。ジョブは流していないので、実行しての確認はまだ。`obs/` は変えていない。

**変えたファイル**

| ファイル | 変更 |
| --- | --- |
| `letkc/obsope_tools_ctl.f90`（新規） | `obs/obsope_tools.f90` の `obsope_cal` だけを写したモジュール `obsope_tools_ctl`（`obsmake_cal`・`obssim_cal` などは LETKC で使わないので写さない）。制御目標の分岐（`ctl_setup`・`ctl_need_slot`・`ctl_accum`・`ctl_finish`） |
| `letkc/Makefile` | `../obs/obsope_tools.o` をやめ、`obsope_tools_ctl.o` を `common_letkc` でコンパイルして `OBJS` に入れる。`-I../obs` と `$(OBS_DIR)` の規則を消す |
| `letkc/letkf.f90` | `use obsope_tools` → `use obsope_tools_ctl` |
| `common_letkc/common_obs_scale.f90` | `monit_obs`（obsdep・departure の統計）: 制御目標は restart の状態から計算できないので、y_b − H(x_b) に観測演算子の値（`obsda_sort%val` = y − 平均 H(x)）を使い、y_a − H(x_a) は undef。QC は y_b のもの（good）を残し、y_a の統計（`monit_dep`）には入れない |
| `src/func_cycle_static.sh` | LETKC の設定ファイルの `SLOT_END` を予報の終わりまで広げる（`slot_e_ctl = slot_e + (CYCLEFLEN − WINDOW_E) / LTIMESLOT`）。広げるとき、history の間隔 ≠ LTIMESLOT か、CYCLEFLEN − WINDOW_E が LTIMESLOT の倍数でなければ止める。LETKF・obsmake の設定は変えない |
| `control/20261107_mpc_soil/submit.sh` | 案 A: `SENS_FCSTOUT=300 SENS_LTIMESLOT=300`（`params.txt` にも書く）。ほかはタスク 4 で直す |

**設計（観測演算子）**

- 観測の割り当て（バケツソート）は変えない。制御目標も「中心（`ri`・`rj`）の subdomain・dif のスロット」に 1 つ割り当てられ、
  そのプロセスの obsda の 1 要素になる（窓の外・領域の外の QC もバケツソートのとおり）。スロットのループの中の点の観測演算子は、制御目標を飛ばす
- 準備（`ctl_setup`。第 1 の走査とバケツソートの後、全プロセス）: `obs(:)` は全プロセスにあるので、各プロセスが自分で
  制御目標の一覧（`OBSDA_RUN` のファイルにあり、領域の中にあるもの）、自分の obsda の中の位置、スロットの重み、自分の subdomain の領域の格子（マスク）を作る。
  通信は領域の格子の数の合計（`MPI_COMM_d`）だけ
  - 変数: `CTL_VAR(typ)` を `v2dd_name`（`common_scale.f90`。今は `topo`・`SFC_PRES`・`PREC`・`U10m`・`V10m`・`T2`・`Q2`）から探す。なければ止める。
    ほかの 2 次元の変数を目標にするときは、`v2dd_name` に足す
  - 時間: スロット k の時刻 τ_k = (k − SLOT_BASE) × SLOT_TINTERVAL（ほかの観測と同じ基準。dif も SLOT_BASE = t + LCYCLE からの秒）。
    窓 (dif − CTL_HALF_T, dif + CTL_HALF_T] に τ_k が入るスロットを使う（時間平均の history は区間の終わりの時刻で書かれるので、窓をちょうど覆う）。
    重みは `'SUM'` なら SLOT_TINTERVAL（5 分平均 × 300 s）、`'MEAN'` なら 1 / スロットの数。
    2 × CTL_HALF_T が SLOT_TINTERVAL の倍数でなければ止める。窓のスロットが SLOT_START〜SLOT_END に揃わなければ `iqc_time`。
    CTL_HALF_T = 0 は dif のスロット 1 つ
  - 領域: 格子の中心が中心から |Δi| × DX ≤ CTL_HALF_X かつ |Δj| × DY ≤ CTL_HALF_Y（1 mm の余裕）。
    今回（中心 x = 80 km・y = 120 km、半幅 10 km）は x 71〜89 km・y 111〜129 km の 10 × 10 = 100 格子（`soil_control.f90` と同じ）。
    格子が 1 つもなければ `iqc_out_h`。二重周期の折り返しは扱わない（領域が境界をまたがないこと）
  - typ が 1〜nobtype の外、`USE_OBS(typ)` が偽、`CTL_VAR(typ)` が空なら `iqc_otype`
- 読み込み: どの観測もないスロットは history を読まない（今の作り）が、制御目標の窓に入るスロットは読む（`ctl_need_slot`）。
  この判断は全プロセスで同じ（`read_history` の halo の通信が同じ member の組で揃う必要がある）
- 部分和（`ctl_accum`。スロットごと）: 自分の subdomain の領域の格子の値の和 × スロットの重み。−1e29 より小さい値（SCALE の欠損）は数える
- 仕上げ（`ctl_finish`。member ごと、スロットのループの後）: 部分和と欠損の数を `MPI_ALLREDUCE`（`MPI_COMM_d`。同じ member の組の全 subdomain）で足し、
  受け持つプロセスが `obsda%val` = 和 / 格子の数（`CTL_AREA_OP = 'MEAN'`）、`qc = iqc_good` を入れる。欠損があれば `iqc_obs_bad`。
  そのあとの `obs_da_value_partial_reduce_iter` で `ensval` に入り、タスク 1 の相対目標・QC・局所 ETKF・obsdep の道を通る
- ログ: `CTLTARGET: number of control targets` と各目標の一覧（rank 0、LOG_LEVEL ≥ 1）、member ごとの H(x)（受け持つプロセスの NOUT、LOG_LEVEL ≥ 2）
- 種類を増やすとき: `is_ctl_obs` に要素を足し、`ctl_setup`（領域・窓の決め方）と `ctl_finish`（値の決め方）の `select case` に分岐を足す。
  領域の最大などは、部分和の代わりに部分の最大を `MPI_MAX` で集める形にする

**history とスロット（案 A）の確かめたこと**

- SCALE の history（`scalelib/src/file/scale_file_history.F90`）は、`FILE_HISTORY_OUTPUT_STEP0 = .true.` のとき、時間平均の変数も step 0 を欠損値（RMISS）で 1 レコード書く。
  なので全体 5 分・PREC も 5 分の時間平均なら、どの変数も「k 番目のレコード = (k − 1) × 300 s」で、`read_history` のスロット k の読み方と合う（窓は step 0 を含まない）
- `obstime` はスロット 1 = t（step 0）、`slot_b` = t + LCYCLE。LTIMESLOT = 300 なら SLOT_BASE = 13、LETKF の SLOT_END = 13、LETKC の SLOT_END = 13 + (4500 − 3600) / 300 = 16。
  窓 (−900, +900] は スロット 11〜16（予報の t + 50〜75 分の 6 つの 5 分平均 = t + 45〜75 分）に入る

**タスク 3・4 への申し送り**

- タスク 4: LETKC の設定ファイル（`config.nml.letkc`）に `&PARAM_CTLTARGET`（タスク 1 の記録の値）を書く。`submit.sh` は `SENS_FCSTOUT=300 SENS_LTIMESLOT=300` を入れたので、
  controltarget（`controltarget_mpc_areaprec`）を置く形と、`SOILCTRL_*` を消すことを残す。PREC の時間平均（`SENS_PREC_TINTERVAL=300`）は history の間隔と同じにしておくこと
- タスク 4 の試験で確かめること: ログの `CTLTARGET #1: ... ncell = 100, slots = 6`、member ごとの H(x)（LOG_LEVEL ≥ 2）が `soil_control.f90` の `SOILCTRL Ymem` と同じ式の値になること、
  obsdep（`obsdep/obsdepcont_<時刻>`）に要素 19001 が qc = 0 で出て、omb = y* − Ȳ、oma が undef であること
- LETKF（step 10）も SLOT_TINTERVAL = 300 になる（13 スロット）。観測は毎時の 1 時刻だけなので結果は変わらない見込みだが、history の読み込みの回数は同じ（観測のないスロットは読まない）
- obsdep の oma（y_a − H(x_a)）は、解析からもう一度予報しないと出せないので undef。修正の効き目は、step 7 の予報し直しの history から Y を計算して確かめる（タスク 4 の Python の検算）
- タスク 3 は観測演算子に触らない（状態変数は restart の側）。`letkf_tools.f90` は制御目標を `is_ctl_obs` で見分けられる
- `obs/obsope_tools.f90` は LETKF・obsope・obsmake のものとして残る。LETKC 用は `letkc/obsope_tools_ctl.f90` だけ直せばよい

### タスク 3（2026-11-07）

`common_letkc/` を make したあと、`letkc/` の .o・.mod を消して `SCALE_SYS=FX700 make letkc` が通ることを確かめた（`letkc` に `set_letkc_control`・`letkc_control_constrain`・`state_var_index` の記号が入っている）。
ジョブは流していないので、実行しての確認はまだ。`soil_control.f90`・`letkf/`・LETKF の設定は触っていない。

**変えたファイル**

| ファイル | 変更 |
| --- | --- |
| `common_letkc/common_nml.f90` | `nv2d` 0 → 2。`&PARAM_LETKC_CONTROL` の変数（`ncontrol_max = 20` 行）と `read_nml_letkc_control`（既定の 1 行目 = QV の制御を入れてから読む。向き・層・範囲・λ の値を確かめる）。`VAR_LOCAL_CTL`（タスク 1 で足したもの）を消した（列 9 はこの設定から作る） |
| `common_letkc/common_mpi_scale.f90` | `set_scalelib` の LETKF の分岐で `read_nml_letkc_control` を呼ぶ |
| `common_letkc/common_scale.f90` | 2 次元の状態変数の表 `v2d_name`（restart の変数名 `'LAND_WATER'`）・`v2d_lz`（層 1・2。0 は (x, y) の変数）・`v2d_label`（設定で使う名前 `'LAND_WATER_1'`・`'LAND_WATER_2'`）。`read_restart`・`write_restart` と PnetCDF 版（`read_restart_par`・`write_restart_par`）で、`v2d_lz > 0` なら lz のその層だけを読み、書くときは同じ層に戻す（start = (lz, x, y)、count = (1, IMAX, JMAX)。ほかの層はファイルのまま）。関数 `state_var_index`（名前 → 状態変数の添字）。`read_restart` の 2 次元の「not found」の表示の誤り（`v3d_name(iv3d)`）を直した |
| `letkc/letkf_tools.f90` | 固定の制御（`var_local(:,4) = 0; var_local(6,4) = 1`、`clev`、`force_check`、`control_lamda`、`control_std3d`・`control_relativenorm3d` と主ループの中の計算）を消し、`set_letkc_control`（変数の局所化の制御の列を作る）と `letkc_control_constrain`（修正の後の制約）に置き換えた |
| `convection/config.nml.letkc` | `&PARAM_LETKC_CONTROL` を既定値（QV の制御）で足した。今回の実験の値はコメントに書いた |

**状態変数（LAND_WATER）**

- restart の `LAND_WATER` は netCDF で (y, x, lz)（Fortran では (lz, x, y)、lz = 7）、時間の次元はない。その第 1・2 層を 2 次元の状態変数 `nv3d + 1`・`nv3d + 2` にした
- 変換（`state_trans`・`state_trans_inv`）は 3 次元の変数だけを扱うので、2 次元はそのまま通る。`POSITIVE_DEFINITE_*` も 3 次元だけ
- 散らす・集める（`scatter_grd_mpi`・`gather_grd_mpi`）、平均・ばらつき（`ensmean_grd`・`enssprd_grd`）、`write_ensmean`・`write_enssprd` はもとから `nv2d` の一般の作り。
  gues・anal の mean と sprd のファイルにも `LAND_WATER` の第 1・2 層が書かれる（その層は member の平均・ばらつきになる。第 3〜7 層は、そのファイルのもとの値のまま）。
  これまでは mean・sprd のファイルの `LAND_WATER` は書き換えていなかったので、そこだけは前と違う
- 観測演算子（history を読む）・`monit_obs`（`state_to_history`）は 2 次元の状態変数を使わない
- 2 次元の変数を足すときは、`nv2d`（`common_nml.f90`）と `v2d_name`・`v2d_lz`・`v2d_label` を直す

**`&PARAM_LETKC_CONTROL`（1 行 = 1 つの状態変数）**

| 変数 | 既定 | 意味 |
| --- | --- | --- |
| `CONTROL_VAR` | 1 行目 `'QV'`、ほか `''` | 状態変数の名前（3 次元は `v3d_name`: `'QV'` など、2 次元は `v2d_label`: `'LAND_WATER_1'`・`'LAND_WATER_2'`）。`''` の行は使わない。同じ変数を 2 行に書くと止める |
| `CONTROL_TARGET` | 1 行目 `'PS'`、ほか `''` | この変数を修正する目標（変数の局所化の列の名前 `obelmlist_varlocal`: `'PS'` = 地上気圧の要素を目標にした従来の制御、`'CTL'` = 要素 19001 などの制御目標） |
| `CONTROL_KMIN`・`CONTROL_KMAX` | 1・1 | 修正する層（3 次元だけ。下から）。この外の層は修正しない |
| `CONTROL_DIRECTION` | 1 行目 `'DECREASE'`、ほか `'BOTH'` | `'DECREASE'`（減らすだけ）・`'INCREASE'`（増やすだけ）・`'BOTH'` |
| `CONTROL_VMIN`・`CONTROL_VMAX` | −1e30・1e30 | 修正した値の範囲（切り詰める） |
| `CONTROL_LAMBDA` | 0 | 信号対雑音比の閾値の係数（0 で使わない） |

- 既定（namelist を書かない、または 1 行目を書き換えない）は、これまでコードに固定していた QV の制御と同じ: 地上気圧の目標で、QV を最下層だけ、減らす向きだけ、λ = 0。
  なお、依頼の文面にあった「`clev`（最下層 3 層）」は、コードの値が `clev = 1`（コメントは「first 3-layer」）だったので、既定は 1 層にした
- 変数の局所化: 制御目標の列（`' PS'`（列 4）・`'CTL'`（列 9）と、`CONTROL_TARGET` に書いた列）は全部 0 にして、表の行の変数だけ 1 にする（`set_letkc_control`。`var_local_n2nc` のまとめの前）。
  ほかの列（`VAR_LOCAL_UV` など）は今のまま namelist から。`VAR_LOCAL_PS` は LETKC では使わない（もとから固定で上書きしていた）
- 制約（`letkc_control_constrain`。主ループの後、もとの制約のあった場所。行ごとに）。Δx = 修正後 − 第一推定（DET_RUN なら mdet、なければ member 平均）:
  1. 3 次元の変数で層 `CONTROL_KMIN`〜`CONTROL_KMAX` の外は、member・mdet とも第一推定に戻す
  2. 層の中で |Δx| / σ（member の第一推定の標準偏差）< `CONTROL_LAMBDA` × （全格子・層の中での最大、`MPI_COMM_a`）の点は戻す（σ = 0 の点は比を 0 とする）
  3. `'DECREASE'` で Δx > 0、`'INCREASE'` で Δx < 0 の点は戻す
  4. 残った点で、変わった値（member・mdet）を [`CONTROL_VMIN`, `CONTROL_VMAX`] に切り詰める（変わっていない値は、範囲の外でもそのまま）
  - 1〜3 の順と「戻す」の中身（member = 平均 + 差、mdet = 第一推定）は、もとのコードと同じ。もとのコードは σ = 0 で 0 除算になっていたが、λ = 0 では結果に効かない
  - ログ（LOG_LEVEL ≥ 1）: `[Info] LETKC control #j: var = ... target = ...`（設定の一覧）、`[Info] LETKC control #j (...): max |dx|/sigma, threshold`、修正が残った点・λ で戻した点・向きで戻した点・切り詰めた値の数・max |Δx|
- 制御しない変数（表にない変数）には制約をかけない（もとの QV 以外と同じ）。目標の列が 0 なので、制御目標だけのときは ETKF で変わらない（member は 平均 + 差 で、もとの 3 次元の変数と同じ扱い）
- member・mdet の更新は今のまま（member は ETKF の変換、mdet は `transmd`）。mdet の増分を member に足すことはしない

**今回の実験の設定（タスク 4 で `config.nml.letkc` の `&PARAM_LETKC_CONTROL` を置き換える）**

```
&PARAM_LETKC_CONTROL
 CONTROL_VAR(1) = 'LAND_WATER_1', CONTROL_TARGET(1) = 'CTL', CONTROL_DIRECTION(1) = 'INCREASE',
 CONTROL_VMIN(1) = 0.0D0, CONTROL_VMAX(1) = 0.5D0, CONTROL_LAMBDA(1) = 0.0D0,
 CONTROL_VAR(2) = 'LAND_WATER_2', CONTROL_TARGET(2) = 'CTL', CONTROL_DIRECTION(2) = 'INCREASE',
 CONTROL_VMIN(2) = 0.0D0, CONTROL_VMAX(2) = 0.5D0, CONTROL_LAMBDA(2) = 0.0D0,
/
```

1 行目を書き換えるので QV は制御しない（列 4 の `'PS'` も全部 0 になる）。

**タスク 4 への申し送り**

- `config.nml.letkc`: 上の `&PARAM_LETKC_CONTROL` と、タスク 1 の `&PARAM_CTLTARGET` を書く。`&PARAM_SOILCTRL` は `soil_control.f90` と一緒に消す
- 試験で確かめること: ログの `[Info] LETKC control #1: var = LAND_WATER_1, target = CTL, 2D, direction = INCREASE, range = 0 - 0.5`、
  `*** Read 2D var: LAND_WATER_1`（LOG_LEVEL ≥ 1）、anal の mdet・member の `LAND_WATER` の第 1・2 層だけが変わり、第 3〜7 層と `LAND_ICE` などが gues と同じこと。
  Python の検算では、ETKF の式（member の平均の移動 `transm`、mdet は `transmd`。下の RTPP に注意）で第 1・2 層の Δθ を出し、増やす向き・0〜0.5 の制約をかけて比べる
- `config.nml.letkc` は `RELAX_ALPHA = 1.0D0`（RTPP で α = 1）なので、member のばらつきは第一推定のまま（member は平均の移動だけ）。計画 1 節の「member は ETKF でばらつきも変換される」は、この設定ではそうならない。どちらにするかはタスク 4 で決める
- 修正量は member の LAND_WATER のばらつき（と Y との共分散）に比例する。土壌水分にはばらつきを足していないので、ばらつきは member の降水の違いから育ったものだけ。ばらつきが 0 の格子は修正されない
- 既定の QV の制御で前と同じ結果になるかは、実行して確かめていない（コードの上では同じ。違うのは、gues・anal の mean・sprd のファイルの `LAND_WATER` の第 1・2 層が平均・ばらつきで書かれること。member・mdet の LAND_WATER は、目標の列が 0 なので 平均 + 差 で書き戻され、丸めの差（最後の桁）が出うる）


### タスク 4（2026-11-07）

迂回の実装を消し、`submit.sh` を新しい流れにつないで、2 member・1 cycle の試験（`test_m2`、debug-o 144 ノード、ジョブ 10188438、18:30 投入・約 8 分）を流した。
全段階（予報 → LETKC → 予報し直し → obsmake → LETKF）が正常に終わり、Python の検算と合った。

**変えたファイル**

| ファイル | 変更 |
| --- | --- |
| `letkc/soil_control.f90` | 消した（git からも外した。改造前の実行ファイル `letkc/letkc.before_soilctrl_20261107` は残っている） |
| `letkc/letkf.f90` | `use soil_control`・`read_nml_soilctrl`・`SOILCTRL_RUN` の分岐を消した |
| `letkc/Makefile` | `soil_control.o` を消した。`SCALE_SYS=FX700 make letkc` が通り、`letkc` に soilctrl の記号がないことを確かめた |
| `convection/config.nml.letkc` | `&PARAM_SOILCTRL` を消し、`&PARAM_CTLTARGET`（タスク 1 の値）を書いた。`&PARAM_LETKC_CONTROL`・`HORI_LOCAL` は既定（QV の制御・20 km）のまま（制御なしの cycle の動きを変えないため） |
| `convection/cycle_run.sh` | `SENS_SOILCTRL_*` の上書きを消した。`SENS_LETKC_NML`（LETKC の設定の雛形をこのファイルに差し替える）、`SENS_HIST_GUES_SAVE`（ジョブの config.main に書く）を足した |
| `convection/src/cycle.sh` | `SENS_HIST_GUES_SAVE=1` のとき、LETKC の前に step 3 の history を `<時刻>/hist_gues/` に写す（step 7 が `hist/` を上書きするので。試験の検算用） |
| `convection/control/20261107_mpc_soil/submit.sh` | 下 |
| `analysis/control/20261107_mpc_soil/check_letkc_ctl_test.py`（新規） | 検算（下） |

**submit.sh**

- 制御目標: `make_obsin/controltarget/controltarget_mpc_areaprec` の値・誤差の欄を引数 `RATIO`（既定 0.8）・`SIGMAR_FACTOR`（既定 1.0）に書き換えて `$OUT/obs/controltarget` に置く。
  比を変えるのに namelist ではなく controltarget の値を使うのは、タスク 1 の決めごと（値 = 比、誤差 = 係数）に合わせたため
- LETKC の設定: `config.nml.letkc` の `&PARAM_LETKC_CONTROL` をタスク 3 の記録の値（LAND_WATER_1・2、`'CTL'`、増やすだけ、0〜0.5、λ = `LAMBDA`）に、
  `HORI_LOCAL` を引数（既定 1.0D6 = 領域全体）に、`LOG_LEVEL` を引数（既定 1）に置き換えた `$OUT/config.nml.letkc` を作り、`SENS_LETKC_NML` で使う。LETKF（step 10）の設定は変えない
- そのほか: `SENS_FCSTOUT=300 SENS_LTIMESLOT=300`（案 A）、`SENS_PREC_TINTERVAL=300`、`SENS_CYCLEFLEN=4500`。
  `HIST_CLEAN`（既定 1）・`KEEP_HIST_GUES`（既定 0）を引数にした（試験は 0・1。member の history・restart を残し、step 3 の history を写す）
- 初期値は result_m80 の START の解析のうち、`MEMBER` 番までの member と mdet・mean・sprd だけを写す（試験で 80 member 分を写さないため）
- 消した引数: `NLAYER`・`INCREASE_ONLY`・`APPLY_MEMBERS`（`&PARAM_LETKC_CONTROL` と、LETKC の member の更新に置き換わった）
- RTPP は `config.nml.letkc` の `RELAX_ALPHA = 1.0D0` のまま（member のばらつきは第一推定のまま、平均だけが動く）。
  タスク 3 の申し送り「どちらにするか」は、ユーザーの決定「member・mdet の更新は今の LETKC のまま」に従い、変えていない

**試験の結果（`/work/gv42/v42013/20260923_enkc_convection/mpc_soil/test_m2/`）**

試験のコマンド: `control/20261107_mpc_soil/submit.sh test_m2 MEMBER=2 RSCGRP=debug-o LAST=20000131130000 TIME_LIMIT=00:30:00 LOG_LEVEL=2 HIST_CLEAN=0 KEEP_HIST_GUES=1`

| 確かめたこと | 結果 |
| --- | --- |
| ジョブ | 正常に終了（`SCALE-LETKF successfully completed`、`scale_rm_ens`・`letkf` が 2 回ずつ `finished successfully`）。予報 20 s、LETKC 26 s、予報し直し 18 s、obsmake 17 s、LETKF 6 s（ほかは restart・history のコピー） |
| PREC の時間平均 | SCALE が受け付けた（`TAVERAGE is obsolete. Use TSTATS_OP instead` の WARN が出るだけ）。history の時刻は 0, 300, …, 4500 s |
| 制御目標 | `CTLTARGET #1: elm = 19001, typ = 1, dif = 0.0, ok = T, ncell = 100., slots = 6, subdomain = 63` |
| H(x)（LOG_LEVEL = 2） | member 1: 1.084839E−03、member 2: 5.752766E−02、mdet（`member 4` と出る）: 3.393839E−02 [mm] |
| QC | after QC で `ADPUPA CTA` が 1（落ちていない） |
| obsdep（`obsdep/obsdepcont_20000131120000.dat`） | 要素 19001、値 y* = 2.3445E−02、誤差 σ_R = 3.9911E−02、qc = 0、omb = −5.8612E−03（= y* − Ȳ）、oma = undef |
| 変数 | `Read 2D var: LAND_WATER_1`・`LAND_WATER_2`、`[Info] LETKC control #1: var = LAND_WATER_1, target = CTL, 2D, direction = INCREASE, range = 0 - 0.5, lambda = 0`（#2 も同じ） |
| 修正量（ログ） | LAND_WATER_1: 修正 7138 点、向きで戻した 7261 点、切り詰め 7 個、max Δ = 2.93E−02。LAND_WATER_2: 7034 点・7366 点・0 個・9.96E−03 |
| 予報の終わりの restart | `20000131131500` を step 3・7 の後に消した。12 時の anal には 12 時の restart だけ、13 時の anal に 13 時の restart |
| obsmake・LETKF（step 8・10） | 止まらずに終わった（13 時の観測 `obs/obs_20000131130000.dat`、`obsdep_20000131130000.dat`） |

注意: `[Info] LETKC control target ...`（Ȳ・σ_Y・y*・σ_R の行）はジョブの出力に出なかった。`LOG_OUT` が偽のプロセス（目標を受け持つ subdomain 63）が書くため。
値は obsdep で確かめられたので、今は直していない（直すなら `letkf_obs.f90` の条件を、受け持つプロセスが書く形にする）。
LETKC の標準出力は `<時刻>/log/letkc/` ではなく、ジョブの出力（`exp/<ジョブ>_cycle_<時刻>/cycle_job.sh.<ジョブ>.out`）に入る。
cycle_run.sh の終わりの `cp: target '.../config/' is not a directory` は設定の控えの処理の表示で、結果には効かない。

**Python の検算（`analysis/control/20261107_mpc_soil/check_letkc_ctl_test.py`、出力は `test_m2/check_letkc_ctl_test.txt`。ログインノードで約 3 分）**

- Y: `hist_gues/` の PREC を中心 ±10 km の 100 格子で平均し、t ∈ (2700, 4500] の 6 つの 5 分平均 × 300 s で足した値は、
  member 1・2・mdet とも LETKC の H(x) と 7 桁で一致
- Ȳ = 2.930625E−02、σ_Y = 3.991110E−02（分母 N − 1）、y* = 2.344500E−02、σ_R = σ_Y。obsdep と一致
- ETKF（観測 1 つ）: P̃a = [(N − 1) I + dYᵀ dY / σ_R²]⁻¹、平均の重み transm = P̃a dYᵀ (y* − Ȳ) / σ_R²、mdet は transmd = P̃a dYᵀ (y* − Y_mdet) / σ_R²。
  member は θ̄ + dX transm + dX_i（RTPP α = 1）、mdet は θ_d + dX transmd。そのあと Δx_mdet ≤ 0 の点を戻し、変わった値を 0〜0.5 に切り詰める
- 結果: 第 1・2 層の anal − gues と、mdet・member 1・2 とも max |差| ≤ 1E−9（restart の単精度の丸め程度）。修正した格子の数も 1 点の差まで合った。
  第 3〜7 層は mdet・member とも gues と同じ
- 参考（2 member なので意味はない）: 予報し直しの Y は member 1: 1.08E−03 → 1.33E−03、member 2: 5.75E−02 → 5.74E−02、mdet: 3.39E−02 → 3.42E−02

**本番への申し送り**

- 本番（80 member・6 cycle）: `control/20261107_mpc_soil/submit.sh <実験名>`（既定で `HIST_CLEAN=1`・`KEEP_HIST_GUES=0`、regular-o・TIME_LIMIT 3 時間）。比べる相手は `RATIO=1.0`
- `HIST_CLEAN=1` では member の history と 12 時の member の restart が LETKF の後に消えるので、member の修正量（anal − gues）は残らない。mdet は `gues/mdet` と `anal/mdet` で残る
- member の第一推定（LETKC の前の restart）は、1 cycle 目はコピー元（result_m80）にあるが、2 cycle 目からはどこにも残らない（LETKC がその場で書き換える）。要るなら cycle.sh で写す
