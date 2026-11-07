# Python 環境（miniconda3）の更新（2026-10-27）

解析に使う `/work/02/gv42/v42013/miniconda3`（base だけ）を、脆弱性への対応で更新した。前の更新は 2026-01-19。

## 更新前の脆弱性

OSV（api.osv.dev）に、入っている PyPI のパッケージ 96 個を照会した。既知の脆弱性があったのは 16 個:
pillow 12.0.0、pip 25.3、cryptography 46.0.3、urllib3 2.6.1、requests 2.32.5、certifi 2026.1.4、tornado 6.5.4、pyjwt 2.10.1、idna 3.11、msgpack 1.1.1、brotlicffi 1.2.0.0、pygments 2.19.2、setuptools 80.9.0、wheel 0.45.1、python-dotenv 1.1.0、pydantic-settings 2.12.0。

## やったこと

1. バックアップ: `/work/02/gv42/v42013/conda_backup_20261027/`
   - `base_explicit.txt`（`conda list --explicit --md5`。戻すときは `conda create -p <場所> --file base_explicit.txt`。defaults の ToS で止まるかもしれない。下の注意）
   - `base_env.yml`・`base_list.txt`・`pip_freeze.txt`
2. `conda update --all`（ログは同じ場所の `update.log`）
3. openssl 3.6.0 は 2 では変わらなかったので、conda-forge から 3.6.5 にした（`conda install --override-channels -c conda-forge openssl=3.6.5`）
4. conda の利用統計の送信（`conda-anaconda-telemetry`）を消した。これだけが使っていた opentelemetry 一式・grpc・protobuf など 17 個も一緒に消えた
   （`conda remove --override-channels -c conda-forge conda-anaconda-telemetry anaconda-opentelemetry opentelemetry-…`）

主な版の変化: numpy 2.3.5 → 2.5.4、scipy 1.16.3 → 1.18.1、matplotlib 3.10.7 → 3.11.2、netCDF4 1.7.3 → 1.7.4、hdf5 1.14.6 → 2.0.0、xarray 2025.12.0 → 2026.9.0、cartopy 0.25.0 → 0.26.0、pandas 2.3.3 → 3.0.6、pillow 12.0.0 → 13.0.0、conda 25.11.1 → 26.9.4。Python は 3.13.11 のまま。
conda-forge から入れていたもの（cartopy・netCDF4・xarray・pandas・hdf5 など）は defaults の版に置き換わった。

## 更新後の脆弱性

PyPI のパッケージ 109 個のうち、残ったのは 1 個:
- setuptools 84.0.0（GHSA-xmj3-9gf7-h52w）: Windows だけの問題。defaults に修正版（84.1.0）がまだない

（opentelemetry-api 1.43.0 の GHSA-xcq7-p3pf-p88h も 3 のあとに残っていた。`anaconda-opentelemetry` が `opentelemetry-api<1.44` を要求して修正版 1.45.1 が入らないので、4 でプラグインごと消した）

## 注意: defaults の利用規約

conda 26.9 にしてから、defaults（repo.anaconda.com/pkgs/main・r）を使う操作は利用規約（ToS）に同意しないと止まる（`CondaToSNonInteractiveError`）。
同意はしていない（大学での利用と Anaconda のライセンスの条件に関わるため、自分で判断する）。同意しないなら、conda-forge のパッケージは `--override-channels -c conda-forge` で入れられる。

## analysis/ のスクリプトの確認

更新後の環境で、analysis/ と docs/ の写しを使って Aquarius（share-debug）で実行し、docs/ にある過去の出力と比べた（docs/ の図は上書きしない）。
ジョブのスクリプトと出力は `/work/02/gv42/v42013/conda_backup_20261027/regtest/`（`regtest_job.sh`・`letkf_job.sh`、出力は `after/out/`・`after/fig/`）。

| スクリプト | 結果 | 過去の出力との比較 |
| --- | --- | --- |
| toy_kf | 正常 | — |
| check_cycles --fast | 正常 | `run_soil_6cycle/check_cycles_fast.out` と数値は同じ（違うのは表示するパスだけ） |
| check_obspoint | 正常 | `run_soil_6cycle/check_obspoint.out` と同じ（図の場所の行だけ違う） |
| check_truth | 正常 | `run_soil_1cycle/check_truth.out` と同じ（図の場所の行だけ違う） |
| check_spinup | 正常 | `check_spinup.out` と同じ（図の場所の行だけ違う） |
| check_onset | 正常 | `run_soil_1cycle/check_onset.out` とまったく同じ |
| check_members | 正常 | `run_soil_1cycle/check_members.out` とまったく同じ |
| check_obsmake | 正常（result/ で） | H の範囲は同じ。O−H の統計は少し違うが、result/obs の観測が 6 cycle の実行（10/7 04:18）で作り直され、記録（01:47）とノイズが違うため |
| check_letkf | 正常（result/ で） | 比べる記録なし |
| compare_sens | 正常 | `sens/compare_sens.out` と数値は同じ（見出しの文言はスクリプトの修正の分だけ違う） |
| plot_1cycle・plot_6cycle・plot_summary・plot_fcst1h | 正常 | 図は見た目で同じ。画素は 6〜12% 違うが、matplotlib 3.11 での文字・線の描き方（アンチエイリアス）の違い |
| offline_letkf | 失敗 | 更新のせいではない。Phase 7（1/1 開始）のデータ用で、今の result/ だと「実際の LETKF の増分」がすべて 0 になり、`np.polyfit` が失敗する。Phase 7 のデータはもうないので確かめられない |

退避した 1 cycle の結果（`result/bak_soil_1cycle_9829615`）には観測ファイルがないので、check_obsmake・check_letkf はそこを指すと止まる（更新とは関係ない）。

結論: 解析の数値は更新の前後で変わらない。
