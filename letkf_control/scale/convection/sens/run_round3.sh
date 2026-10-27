#!/bin/bash
#===============================================================================
# 感度実験の 3 回目（2026-10-16）: 1 点観測試験と、自由度を増やす組み合わせ（計画書の「感度実験 3 回目」）
#   S1U・S1T: 1 点観測試験。C' の 5 時の解析から始め、6 時の LETKF だけを 4 つの孤立した観測（U・T）で行う
#   L5:       HORI_LOCAL 5 km
#   M40L10:   40 member + HORI_LOCAL 10 km
#   M80:      80 member（PPN 8・THREADS 6、1 member 18 ノード）。init/make_m80.sh の初期値ができてから
#   M80L10:   80 member + HORI_LOCAL 10 km
# 6 時間の実験は、終わったら評価（eval_job.sh、Aquarius share-short）を投げる。
# tmux の中で動かす。記録: /work/gv42/v42013/20260923_enkc_convection/sens/run_round3.log
#===============================================================================
cd "$(dirname "$0")"
BASE=/work/gv42/v42013/20260923_enkc_convection
exec >> $BASE/sens/run_round3.log 2>&1
echo "===== [$(date '+%F %T')] run_round3.sh 開始（$(hostname)）"

run() {   # 実験名 [KEY=値 ...]。6 時間の実験なら終わったあと評価を投げる
  local n=$1
  ./submit.sh "$@" || return 1
  case $n in S1*) ;; *)
    pjsub -x NAMES=$n -L rscgrp=share-short -L elapse=01:00:00 -o $BASE/sens/eval_$n.out eval_job.sh
    echo "[$(date '+%F %T')] $n の評価を投入" ;;
  esac
}

pids=()
run S1U START_FROM=Cp START_TIME=20000131050000 OBS_DIR=$BASE/sens_obs/S1U TIME_LIMIT=00:40:00 & pids+=($!); sleep 90
run S1T START_FROM=Cp START_TIME=20000131050000 OBS_DIR=$BASE/sens_obs/S1T TIME_LIMIT=00:40:00 & pids+=($!); sleep 90
run L5 HORI_LOCAL=5.0D3 & pids+=($!); sleep 90
run M40L10 MEMBER=40 INIT=init_soil_m40 HORI_LOCAL=1.0D4 TIME_LIMIT=03:00:00 & pids+=($!); sleep 90
until [ -f $BASE/init_soil_m80/md5.txt ] && [ $(wc -l < $BASE/init_soil_m80/md5.txt) -eq 11664 ]; do sleep 60; done
echo "[$(date '+%F %T')] 80 member の初期値ができた"
run M80 MEMBER=80 INIT=init_soil_m80 PPN=8 THREADS=6 TIME_LIMIT=04:00:00 & pids+=($!); sleep 90
run M80L10 MEMBER=80 INIT=init_soil_m80 PPN=8 THREADS=6 HORI_LOCAL=1.0D4 TIME_LIMIT=04:00:00 & pids+=($!)
for p in "${pids[@]}"; do wait $p || echo "[$(date '+%F %T')] 失敗したものがある（pid $p）"; done
echo "===== [$(date '+%F %T')] run_round3.sh 終了"
