# Phase 1 — case_tc の依存関係の確定：計画書から移した詳細

準備の計画書（`../20260923_experiment_plan.md`）を簡潔にしたとき（2026-11-06）に、そこから移した詳細。中身は書いた当時のまま。
パスはフォルダの整理（2026-11-06）の前のもの（`init/` → `setup/init/` など。対応は `convection/README.md`）。節の番号は、もとの計画書のもの。

## 経緯（もとの改訂履歴から）

  - Phase 1: case_tc の依存関係を調査（`docs/phase1/dependency.md`）。静的入力は `convection/dat/` にコピーする

## 進捗のチェックリスト（もとの「進捗状況」から）

- [x] Phase 1 — case_tc の依存関係の確定 — 2026-09-25
  - [x] スクリプト → 実行ファイル → 設定の対応表 — 2026-09-25（`docs/phase1/dependency.md`）
  - [x] `scale-rm_init_ens`（step 2, 6）が陸面状態を上書きしないか — 2026-09-25（上書きしない。step 2・6 は飛ばされる）
  - [x] LETKC / LETKF での陸面変数の扱い — 2026-09-25（触らない。大気 11 変数だけ）
  - [x] controltarget の入力形式 — 2026-09-25

## case_tc（cycle framework）と step（もとの 2.1 節）

| パス | 性質 |
| --- | --- |
| `letkf_control/scale/run/src/` | cycle スクリプト本体（**複製元**） |
| `letkf_control/scale/run/config/case_tc/` | case_tc のケース設定（**参考**。namelist の `!--XXX--` マーカーの位置を引き継ぐ） |
| `letkf_control/scale/tmp/<TMPSUBDIR>/` | `cycle_run.sh` が実行ごとに作り直す作業領域。**移植元ではない** |

### step とは

1 回の cycle（時刻 t → t+1h）は、決まった順番の処理でできている。
cycle スクリプトはこの処理に 1〜11 の番号を付けていて、これを **step** と呼ぶ
（定義は `src/func_cycle_static.sh`、`DET_RUN_UPDATE=2` のとき）。
`cycle_run.sh` の引数 `ISTEP`・`FSTEP` で、何番の step から何番の step までを実行するかを指定できる。

| step | 実行ファイル | やること | convection での扱い |
| --- | --- | --- | --- |
| 1 | `scale-rm_pp_ens` | 地形・土地利用のファイルを作る | **飛ばす**（地形なし・全面陸） |
| 2 | `scale-rm_init_ens` | 初期値をゼロから作る | **飛ばす**（`BDY_FORMAT=5`。初期値は Phase 4 で用意） |
| **3** | `scale-rm_ens` | **全 member（0001〜0020・mean・mdet）の 1 時間予報** | 実行する |
| **4** | `letkc` | **LETKC**: step 3 の予報と controltarget から、mdet の初期値を修正する（制御） | 実行する |
| 5 | `scale-rm_pp_ens` | step 1 と同じ | 飛ばす |
| 6 | `scale-rm_init_ens` | step 2 と同じ | 飛ばす |
| **7** | `scale-rm_ens` | **修正後の mdet を含めて、1 時間予報をやり直す**（全 member） | 実行する |
| **8** | `obsmake` | **mdet の予報から観測を作る** | 実行する |
| 9 | `obsope` | 観測演算子を単独で計算する | 飛ばす（step 10 の中で計算する） |
| **10** | `letkf` | **LETKF**: 観測を使って 0001〜0020 の解析値を作る。これが次の cycle の初期値になる | 実行する |
| 11 | `efso` | 観測の影響評価 | 飛ばす（`EFSO_RUN=0`） |

#### 図解: 1 cycle（t → t+1h）の流れ（convection で実行する step だけ）

```text
 時刻 t の初期値                                                 時刻 t+1h
 anal/{0001..0020, mean, mdet}
        │
        │ step 3  scale-rm_ens ─ 全 member を 1 時間予報
        ├──────────────────────────────────────────────────▶ 予報（1 回目）
        │                                                         │
        │                                     controltarget ──┐   │
        │                                                     ▼   ▼
        │ step 4  letkc ◀──────────────────────── 1 回目の予報と目標を比べる
        │   │
        │   └─▶ 時刻 t の mdet の初期値を修正（制御）
        │        （修正前の mdet は gues/mdet/ に取っておく）
        │
        │ step 7  scale-rm_ens ─ 修正後の mdet を含めて 1 時間予報をやり直す
        ├──────────────────────────────────────────────────▶ 予報（2 回目）
                                                                  │
                                    OBSIN（観測の位置）──┐        │
                                                        ▼        ▼
                              step 8  obsmake ◀─ mdet の 60 分の予報から観測を作る
                                         │
                                         ▼
                                   obs/obs_<t+1h>.dat
                                         │
                                         ▼
                              step 10 letkf ◀─ 2 回目の予報（0001〜0020）＋ 観測
                                         │
                                         ▼
                         anal/{0001..0020, mean}（t+1h）─▶ 次の cycle の初期値
                         （mdet は LETKF では変えない。DET_RUN_UPDATE=2）
```

- **予報は 1 cycle に 2 回**走る。1 回目（step 3）は LETKC が「このままだとどうなるか」を見るため、
  2 回目（step 7）は制御後の mdet を含めた本番の予報。
- **制御（step 4）が触るのは時刻 t の mdet だけ**。0001〜0020 は制御されない。
- **観測（step 8）は制御後の mdet の予報から作る**。LETKF（step 10）はその観測を 0001〜0020 に同化する。
- 途中の step から再開する（`ISTEP > 3`）と `gues/` の扱いで失敗するので、毎回 step 1 から流す（`docs/phase7/phase7_notes.md`）。

入出力のファイルなど詳しいことは `docs/phase1/dependency.md` の 2 節にある。

この構造は変更しない。

## rep_asakura（物理設定・初期値）（もとの 2.2 節）

| rep_asakura のファイル | convection での扱い |
| --- | --- |
| `1/` – `21/` の `init_20000101-000000.000.pe*.nc` | `$OUTDIR/<STIME>/anal/{0001..0020,mdet}/` に取り込む |
| `init.conf_base` | `init/init.conf_base`（再生成用）と `config.nml.scale_init` の元にする。格子・分割は変えない |
| `run.conf` | `config.nml.scale` の元にする。`!--XXX--` マーカーを入れ、静的入力を `convection/dat/` の絶対パスにする |
| `ensinit.sh`, `init.sh_base` | `init/` に OUTDIR 直接出力版として作る（再生成用） |
| `ensperturb/`（env.txt, env_perturb1–21, sounding_perturb.py） | `init/ensperturb/` にコピー（乱数を振り直さない） |
| 静的入力（PARAG.29 など） | `dat/` にコピー |
| `preprocess_init.sh`, `letkfinput/` | 使わない |

## member の扱い（もとの 3 節）

```text
0001–0020 : ensemble（LETKC の guess、LETKF の ensemble）
mdet       : deterministic / control（21番目の member として扱わない）
```

## Phase 1 の手順（もとの 5 節）

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
