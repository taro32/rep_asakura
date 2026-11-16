# 土壌水分のアンサンブルのばらつきの保ち方：既往研究のレビュー（2026-11-07）

notes.md 1.4 の「土壌水分のばらつきの保ち方」を決めるための材料。
逐次の制御（MPC）では、cycle の member の土壌水分のばらつきが約 0.001 しかなく（3.3・3.4 節）、
このままでは LETKC の cov(θ, Y) が雑音になる。既往研究がこの問題にどう対応しているかを調べた。

## 1. まとめ

- 土壌（地表付近）のアンサンブルのばらつきが小さすぎる（under-dispersive）ことは、結合した陸面・大気のアンサンブルで広く知られた問題。
  原因は、陸面のモデル誤差を表していないこと・member 数・サンプリング誤差（Draper 2021、Lim et al. 2023、Bauser et al. 2018）
- 対応は大きく 4 つ。どれも「ばらつきを外から足す」もので、モデルが自然に保つことは期待されていない

| 方法 | 中身 | 主な例 | 今回に当てはめると |
| --- | --- | --- | --- |
| A. 予報の初めに摂動を入れる | 予報（cycle）の初期値の土壌水分に、空間相関のある乱数を足す | Sutton et al. 2006、COSMO-DE-EPS（Peralta et al. 2012）、Lavaysse et al. 2013、Finn et al. 2022（初期だけ） | 3.5 節のパッチ型の摂動（標準偏差 0.02）を、毎 cycle の step 3 の前に入れ直す |
| B. 予報の途中で摂動を入れ続ける | モデルの時間刻みごとに、土壌の状態（または傾向）に時間・空間相関のある乱数を足す | オフラインの陸面の同化（Kumar et al. 2014、De Lannoy & Reichle 2016）、Draper 2021 の state-pert・soil-SPPT、Lim et al. 2023 の SPSS | SCALE の陸面のコードの変更が要る |
| C. inflation | member の平均からのずれを、毎 cycle 何倍かに広げる | Finn et al. 2022（乗算 1.006 / cycle）、Bauser et al. 2018・Dibia et al. 2023（適応型） | もとのばらつきが 0.001 なので、0.02 にするには 20 倍。空間の形は今の偶然のずれのまま |
| D. 陸面のパラメータを member ごとに変える | 植生の割合などを摂動し、その結果として土壌水分がばらつく | Draper 2021（param-pert、NCEP で推奨）、MacLeod et al. 2016 | バケツ型の土壌でどのパラメータを使うかから考える必要がある |

- **予報のアンサンブル**（数日以内の天気予報）は、ほぼ A（予報の初めに 1 回）。
  **cycle を回し続ける同化の系**は、B か C で、時間とともに変わる摂動を一定の間隔で入れ続けている（Draper 2021 の 1 節の整理）
- 今回の設定に最も近いのは Finn et al. 2022。2.8 km の対流許容モデルと陸面の結合、LETKF で毎時、土壌水分だけを更新する双子実験。
  初めに空間相関のある摂動を入れ、毎 cycle わずかな乗算の inflation を足して、ばらつきが誤差と同じくらいに保たれた
- 土壌水分を 0〜上限に切り詰めると、摂動が上限・下限の近くで片側に偏る（Ryu et al. 2009。Draper 2021 は flat-top filter で対処）。
  今回のパッチ型の摂動の切り詰め（0〜0.5）でも同じことが起こりうる
- 土壌水分の摂動を EnKC（制御）に使った研究は見つからなかった。EnKC の研究（Sawada 2024 ほか）は Lorenz-63・Lorenz-96 などの理想的なモデル

## 2. 文献ごとのメモ

### 陸面・大気の結合したアンサンブルのばらつき

- **Draper (2021)**, J. Hydrometeor., 22, 2089–2104. NCEP の GFS/GDAS（Noah 陸面、4 層）
  - 運用のアンサンブルは陸面とその近くでばらつきが小さすぎ、陸面の同化に使えない
  - 3 つの方法を 1 か月回して比べた
    - state-pert：土壌水分（0.1 mm/h）・地温（0.1 K/h）に毎時間刻みで乱数を足す。水平の相関距離 1000 km・時間の相関 24 h
    - soil-SPPT：土壌の傾向に SPPT をかける
    - param-pert：植生の割合を摂動する
  - state-pert は土壌水分のばらつきの空間分布が不自然になり、soil-SPPT は作れるばらつきに限りがあった。param-pert が現実的なばらつきを作ったので推奨
  - 土壌水分の切り詰めによる偏りを flat-top filter で抑えた。予報のアンサンブルは初めに 1 回、cycle を回す同化の系は一定の間隔で摂動を入れる、という違いも整理している
- **Lim, Park & Cassardo (2023)**, GMD Discuss.（gmd-2023-28。改訂は受理されなかった）. WRF-Noah の SPSS
  - 第 1 層の地温・土壌水分に、時間・空間相関のある乱数を予報の途中で足す
  - 振幅・相関距離・時間スケールを、昼と夜で別に遺伝的アルゴリズムで最適化した
  - 土壌のばらつきは適切になったが、境界層の大気への伝わりは弱い。土壌水分による水蒸気の解析の改善には、さらに工夫が要る
  - 下の層まで摂動すると悪くなったので、第 1 層だけにした
- **Finn, Geppert & Ament (2022)**, arXiv:2209.13902（Atmos. Sci. Lett. に投稿中とある）. TerrSysMP（COSMO 2.8 km + CLM 1 km）、40 member
  - 毎時の 2 m 気温（双子実験）を LETKF で同化し、土壌水分だけを更新した
  - 初期の摂動：土壌水分の飽和度に標準偏差 0.06、地温に 1 K。ガウス核で空間相関（水平 14 km・鉛直 0.5 m）をつけた
  - 毎 cycle、乗算の inflation 1.006 を「アンサンブルの崩れを防ぐため」に入れた。ばらつきは誤差とほぼ同じに保たれた
  - 土壌から大気への情報は遅れて伝わり、効くのは日中（正午ごろが最大）
- **Bauser et al. (2018)**, HESS, 22, 4921. 土壌水文の EnKF
  - ばらつきの不足の原因は、表されていないモデル誤差と member 数の不足（inbreeding）
  - EnKF の中で inflation の係数を推定する方法を提案した
- **Dibia et al. (2023)**, J. Hydrometeor. 土壌水分の同化で、EnKF と rank histogram filter を比べた。適応型の inflation も作った
- **Maggioni, Anagnostou & Reichle (2012)**, HESS, 16, 3499. NASA Catchment 陸面モデル
  - 状態の摂動だけでは土壌水分の不確かさを表しきれなかった
  - 雨の入力とパラメータの摂動を組み合わせると、いちばんよいアンサンブルになった

### 対流と土壌水分の摂動（予報のアンサンブル）

- **Sutton, Hamill & Warner (2006)**, MWR, 134, 3174–3189. WRF
  - 土壌水分の解析だけが違う 2 member で、夏の 6 事例を 1 日予報した
  - 5 km（対流を陽に解く）では、土壌水分の違いによるばらつきが、20 km での積雲パラメタリゼーションの違いと同じくらいになった
  - 土壌水分が中くらいの事例で、陸面の摂動が短期予報の雨・地上気温のばらつきを増やすと結論した
- **Duda, Wang & Xue (2017)**, MWR. 陸面モデルの摂動は、ほとんどの対流許容アンサンブルで系統的に扱われていない誤差の源だと整理した
- **Schneider et al. (2019)**, ACP Discuss.（acp-2019-229）. 弱い総観場の日に、不均一な土壌水分の摂動は主に対流の発生の遅れに効き、降水の始まりにはあまり効かなかった。
  3.5 節（パッチ型の摂動で動くのは降り始めだけ）と同じ傾向
- **COSMO-DE-EPS**（Peralta et al. 2012）・**Lavaysse et al. (2013)**. 予報の初めに、空間相関のある 2 次元の乱数で土壌水分・地温を摂動した。
  原文は未確認（COSMO の資料・Arpa Piemonte の発表からの引用）

### EnKC（制御）

- **Sawada (2024)** ほか. EnKC は、目標を疑似観測として同化し、系に足す摂動を得る。
  実験は Lorenz-63・Lorenz-96 などの理想的なモデルで、土壌水分や降水の制御に使った例は見つからなかった

## 3. 今回の判断に関わる点

- A（毎 cycle 入れ直す）は、3.5 節で実際に使い、どこを湿らせた member で雨が少ないかの信号が出た方法。予報のアンサンブルで一般的なやり方とも合う
- C（inflation）は、Finn et al. 2022 のように、初めに十分なばらつきを入れたうえで、少しずつ保つ使い方が多い。
  今のばらつき（0.001）から 0.02 まで広げるのは、文献の使い方（1.006 倍 / cycle）とは桁が違う
- A・C のどちらでも、摂動を「感度の予報と LETKC にだけ使い、同化の member には残さない」か、「同化の member にも残す」かを決める必要がある。
  今回の LETKF は土壌水分を更新しないので、残すと土壌水分のばらつきは cycle をまたいで残る
- 切り詰め（0〜0.5）による偏り（Ryu et al. 2009）は、目標領域が乾いた側（3.2 節）なので下限の側で起こりうる

## 4. 確かめていないこと

- Hacker & Snyder (2005, MWR, 133, 3260–3275)・Lin & Pu (2020, MWR, 148, 2863–2888)：本文を読めていない。
  題名からは、それぞれ境界層での 2 m 観測の EnKF 同化、EnKF で土壌水分を制御変数に加えたもの
- Peralta et al. (2012)・Lavaysse et al. (2013)・Kumar et al. (2014)・De Lannoy & Reichle (2016)・Ryu et al. (2009)：原文は未確認。
  上の論文の中での引用から書いた

## 出典

- Draper (2021): https://repository.library.noaa.gov/view/noaa/44353 （doi:10.1175/JHM-D-21-0016.1）
- Lim et al. (2023): https://gmd.copernicus.org/preprints/gmd-2023-28/
- Finn et al. (2022): https://arxiv.org/abs/2209.13902
- Bauser et al. (2018): https://hess.copernicus.org/articles/22/4921/2018/
- Dibia et al. (2023): https://www.cisl.ucar.edu/opensky-publications/articles:26484/non-gaussian-ensemble-filtering-and-adaptive-inflation-for-soil-moisture-data-assimilation
- CLM-DART の適応型 inflation（Raczka et al. のポスター, 2023）: https://ntrs.nasa.gov/api/citations/20230009366/downloads/raczka_aimesposter_2023.pdf
- Maggioni et al. (2012): https://hess.copernicus.org/articles/16/3499/2012/
- Sutton et al. (2006): https://ams.confex.com/ams/Annual2006/techprogram/paper_104447.htm
- Duda et al. (2017): https://twister.caps.ou.edu/papers/Duda_Etal_MWR2017.pdf
- Schneider et al. (2019): https://acp.copernicus.org/preprints/acp-2019-229/acp-2019-229-AR1.pdf
- COSMO の対流許容アンサンブルの資料（TR 39）: https://www.cosmo-model.org/content/model/cosmo/techReports/docs/techReport39.pdf
- Sawada の EnKC: https://arxiv.org/abs/2405.08387v1 ・ https://npg.copernicus.org/articles/32/293/2025/npg-32-293-2025.pdf
