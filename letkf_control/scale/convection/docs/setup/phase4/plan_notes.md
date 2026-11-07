# Phase 4 — 初期値を OUTDIR に取り込む：計画書から移した詳細

準備の計画書（`../20260923_experiment_plan.md`）を簡潔にしたとき（2026-11-06）に、そこから移した詳細。中身は書いた当時のまま。
パスはフォルダの整理（2026-11-06）の前のもの（`init/` → `setup/init/` など。対応は `convection/README.md`）。節の番号は、もとの計画書のもの。

## 経緯（もとの改訂履歴から）

  - Phase 4: 初期値の取り込みで、STIME の mean にも mdet（rep_asakura の `21/`）をコピーする

## 進捗のチェックリスト（もとの「進捗状況」から）

- [x] Phase 4 — 初期値を OUTDIR に取り込む（md5 一致を確認） — 2026-09-25（22 member、`docs/phase4/import_result.md`）

## 初期値と cycle のつなぎ方（もとの 1.3 節）

- cycle は `MAKEINIT=0` で `$INDIR/$STIME/anal/<member>/init_*.nc` を読む
  （`src/func_cycle_static.sh` の `RESTART_IN_PATH`）。`INDIR=$OUTDIR` とする。
- **2 km のままなので、rep_asakura で作成済みの初期値をそのまま使える。**
  `init/import_rep_asakura.sh` で次のように `$OUTDIR/$STIME/anal/` にコピーする。

  | rep_asakura | OUTDIR | 摂動サウンディング |
  | --- | --- | --- |
  | `1/` – `20/` | `anal/0001/` – `anal/0020/` | env_perturb1–20 |
  | `21/` | `anal/mdet/` | env_perturb21 |
  | `21/` | `anal/mean/` | env_perturb21（Phase 4 で追加。case_tc と同じく STIME の mean は mdet のコピー） |

  1 member あたり約 143 MB（144 プロセス分の `init_20000101-000000.000.pe*.nc`）で、合計約 3 GB。
- 取り込み後、cycle が読むのは `$OUTDIR` だけとする（rep_asakura を直接参照しない）。
- 初期値テンプレートには `RANDOM_THETA=0.1` があり、作り直すと既存の初期値とは別のアンサンブルになる可能性がある。
  そのため既存の初期値を優先して使い、`init/ensinit.sh`（OUTDIR に直接出力する版）は
  STIME を変える場合（スピンアップ後に開始する場合など）の再生成用とする。
- `init/` のスクリプトは `../config.main` と `../config.cycle` を読み込み、
  `OUTDIR`・`STIME`・`MEMBER` を cycle と共通の値で使う（設定の二重管理をしない）。
- メンバー対応（`1–20 → 0001–0020`、`21 → mdet`）は `init/` のスクリプトの1か所だけで定義する。
- **（2026-10-03）初期値の摂動を土壌水分に変える方針になった（Phase 7d）。** 上の表の「摂動サウンディング」（下層の水蒸気の摂動）は、
  これまでの初期値の作り方。2026-10-03 時点の取り込み元は `init_20261003`（`sounding_perturb.py` の不具合を直した水蒸気の摂動）で、
  土壌水分の摂動は入っていない。

## Phase 4 の手順（もとの 5 節）

- `init/import_rep_asakura.sh` を作り、1.3 節の対応表どおりに `$OUTDIR/$STIME/anal/{0001..0020,mdet}/` へコピーする。
- コピー後の md5 が Phase 0-3 の記録と一致することを確認する。
- STIME を 20000101 以外にする場合（0-4 の (a)）は、スピンアップ後の restart を同じ形で取り込むか、
  `init/ensinit.sh` で再生成する。

### 完了条件

`$OUTDIR/$STIME/anal/` に 20 + mdet の初期値がそろっている。
