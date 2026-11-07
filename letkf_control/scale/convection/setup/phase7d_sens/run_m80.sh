#!/bin/bash
#===============================================================================
# 80 member の 2 本をやり直す（2026-10-16）。1 回目（PPN 8・THREADS 6）は、実行ファイルがスレッド 12 に固定
# （-Kinstance=12）のため起動できなかった。1 member 36 ノードのまま全体を 1476 ノードにし、member を 2 回に分けて流す。
# 記録: /work/gv42/v42013/20260923_enkc_convection/sens/run_m80.log
#===============================================================================
cd "$(dirname "$0")"
BASE=/work/gv42/v42013/20260923_enkc_convection
exec >> $BASE/sens/run_m80.log 2>&1
echo "===== [$(date '+%F %T')] run_m80.sh 開始（$(hostname)）"
run() {
  local n=$1
  ./submit.sh "$@" || return 1
  pjsub -x NAMES=$n -L rscgrp=share-short -L elapse=01:00:00 -o $BASE/sens/eval_$n.out eval_job.sh
  echo "[$(date '+%F %T')] $n の評価を投入"
}
run M80 MEMBER=80 INIT=init_soil_m80 NNODES=1476 TIME_LIMIT=05:00:00 & p1=$!
sleep 120
run M80L10 MEMBER=80 INIT=init_soil_m80 NNODES=1476 HORI_LOCAL=1.0D4 TIME_LIMIT=05:00:00 & p2=$!
wait $p1 || echo "[$(date '+%F %T')] M80 が失敗"
wait $p2 || echo "[$(date '+%F %T')] M80L10 が失敗"
echo "===== [$(date '+%F %T')] run_m80.sh 終了"
