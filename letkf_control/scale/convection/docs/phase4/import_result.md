# Phase 4 — 初期値を OUTDIR に取り込む（2026-09-25 実行）

## 実行したもの

```bash
cd letkf_control/scale/convection/init
./import_rep_asakura.sh /work/gv42/v42013/20260923_enkc_convection/result
```

`config.main` はまだない（Phase 5 で作る）ので、OUTDIR は引数で渡した。
Phase 5 以降は引数を省略すれば `../config.main` の OUTDIR を使う。

## member の対応

| rep_asakura | OUTDIR（`20000101000000/anal/`） | 摂動サウンディング |
| --- | --- | --- |
| `1/` – `20/` | `0001/` – `0020/` | env_perturb1–20 |
| `21/` | `mdet/` | env_perturb21 |
| `21/` | `mean/` | env_perturb21（mdet と同じもの） |

### mean を置いた理由

計画書の当初の対応表には mean がなかったが、cycle の step 3 は 0001–0020・mdet に加えて mean も予報するので、
STIME の `anal/mean/` に初期値がないと止まる。

case_tc（`/work/gv42/v42013/20260603_enkc/result_10/case_tc/20000101000000/anal/`）を調べると、
STIME の mean は **mdet と md5 が完全に一致**し、アンサンブル平均とは違っていた（RHOT の差の最大 0.18 K）。
つまり case_tc でも、STIME の mean は mdet のコピーを置き場所として使っている。
次の時刻の mean は LETKC・LETKF が計算し直して上書きするので、STIME の mean の中身は結果に影響しないと考えられる。
convection も case_tc にそろえて、`21/` を mean にもコピーした。

## 結果

- 22 member × 144 ファイル = **3,168 ファイル**をコピーした（所要 1 分 16 秒、`du` で 2.3 GB）。
- **すべてのファイルの md5 が `docs/phase0/init_1-21.md5` の記録と一致した**（mean は `21/` の記録と照合）。
- コピー元は読み取り専用なので、コピー先にも書き込み権限がなかった。
  LETKC・LETKF は restart をその場で上書きするので、コピー後に `chmod u+w` を付けた。3,168 ファイルすべてに書き込み権限があることを確認した。
- コピー先にすでにファイルがあると止まることを確認した（2 回目の実行で `[Error] ... 上書きしないので止めます。`）。
- コピー元（rep_asakura の `1/`–`21/`）は読み取り専用のまま、変更していない。
