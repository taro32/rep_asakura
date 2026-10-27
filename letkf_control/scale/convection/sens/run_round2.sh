#!/bin/bash
#===============================================================================
# 感度実験の 2 回目（2026-10-15）: QC・同化の間隔・member 数（計画書の「感度実験 2 回目」）
#   Q10・Q99: GROSS_ERROR 10・99（基準の観測で）
#   T60・T30・T15: 同化の間隔 60・30・15 分（自分で観測を作る。T60 は観測のノイズだけが基準と違う比較用）
#   M40: 40 member（init/make_m40.sh の初期値ができてから）
# tmux の中で動かす。記録: /work/gv42/v42013/20260923_enkc_convection/sens/run_round2.log
#===============================================================================
cd "$(dirname "$0")"
BASE=/work/gv42/v42013/20260923_enkc_convection
exec >> $BASE/sens/run_round2.log 2>&1
echo "===== [$(date '+%F %T')] run_round2.sh 開始（$(hostname)）"
pids=()
for args in "Q10 GROSS_ERROR=10.0D0" \
            "Q99 GROSS_ERROR=99.0D0" \
            "T60 OWN_OBS=1" \
            "T30 LCYCLE=1800 LTIMESLOT=600 FCSTOUT=600 OWN_OBS=1 TIME_LIMIT=03:00:00" \
            "T15 LCYCLE=900 LTIMESLOT=300 FCSTOUT=300 OWN_OBS=1 TIME_LIMIT=06:00:00"; do
  ./submit.sh $args & pids+=($!)
  sleep 90                                   # 初期値のコピーと tmp の準備が重ならないように少しずらす
done
# M40: 初期値（41 × 144 = 5904 行の md5.txt）ができるまで待つ
until [ -f $BASE/init_soil_m40/md5.txt ] && [ $(wc -l < $BASE/init_soil_m40/md5.txt) -eq 5904 ]; do sleep 60; done
echo "[$(date '+%F %T')] 40 member の初期値ができた"
./submit.sh M40 MEMBER=40 INIT=init_soil_m40 TIME_LIMIT=03:00:00 & pids+=($!)
for p in "${pids[@]}"; do wait $p || echo "[$(date '+%F %T')] 失敗したものがある（pid $p）"; done
echo "===== [$(date '+%F %T')] run_round2.sh 終了"
