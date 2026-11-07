# Phase 0 の記録（2026-09-25）

## このフォルダは何か

実行ファイル（`letkc`、`scale-rm_ens` など）は git に入れていない。
そのため、後で再ビルドされて中身が変わっても気づけない。

そこで、2026-09-25 時点の各ファイルの **md5** を記録しておく。
md5 はファイルの中身から計算する 32 桁の番号で、中身が 1 バイトでも変わると別の番号になる。
後で同じ計算をして番号が一致すれば、「実験したときと同じファイル」だと確認できる。

| ファイル | 中身 |
| --- | --- |
| `executables.txt` | 実行ファイルの大きさ・作成日・md5 |
| `rep_asakura_scripts.md5` | rep_asakura のスクリプト・設定・摂動ファイルの md5 |
| `environment.txt` | 記録したときの git のコミット番号とタグ、読み込んでいた module |
| `init_1-21.md5` | rep_asakura の初期値 `1/`–`21/`（21 member × 144 ファイル）の md5。Phase 4 で OUTDIR にコピーした後、この番号と一致するか確かめる |

## rep_asakura の生成物は読み取り専用にした

`scale-rm/test/case/rep_asakura/` の `1/`–`101/` と `letkfinput/` は、誤って上書き・削除しないように書き込み禁止にした（`chmod -R a-w`）。
もう一度書き込む必要ができたときは、対象を絞って戻す。

```bash
chmod -R u+w scale-rm/test/case/rep_asakura/<対象>
```

## 実行ファイルが変わっていないか確かめる方法

```bash
cd /work/02/gv42/v42013/scale-letkc
sed -n '/^## md5sum/,$p' letkf_control/scale/convection/docs/phase0/executables.txt | tail -n +2 | md5sum -c
```

すべて `OK` と出れば、記録したときと同じファイル。

## 注意: 初期値を作るプログラムに新旧 2 つの版がある

2026-07-16 に `scale-rm/src/preprocess/mod_mkinit.F90`（初期値を作るプログラムのソース）を書き換えた。

| 実行ファイル | 作成日 | 書き換えを含むか | 用途 |
| --- | --- | --- | --- |
| `bin/scale-rm_init` | 2026-07-18 | 含む（新しい版） | rep_asakura の初期値を作った |
| `letkf_control/scale/ensmodel/scale-rm_init_ens` | 2026-06-02 | 含まない（古い版） | cycle の中で毎回使う |

cycle の中で `scale-rm_init_ens` が書き換えた部分を使うかどうかは、まだ分からない。
使うのであれば `scale-rm_init_ens` を作り直す必要がある。Phase 1 で確認する。
