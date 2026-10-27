#!/bin/bash
#===============================================================================
# 感度実験が終わるたびに評価のジョブ（eval_job.sh、Aquarius share-short）を投げる（tmux の中で動かす）
#   sens/eval_watch.sh <実験名> ...
# 実験の完了は submit.sh のログ（"<実験名>: 完了"）で判断する。記録: sens/eval_watch.log
#===============================================================================
cd "$(dirname "$0")"
BASE=/work/gv42/v42013/20260923_enkc_convection
exec >> $BASE/sens/eval_watch.log 2>&1
echo "===== [$(date '+%F %T')] eval_watch.sh 開始（$(hostname)）: $*"
todo=("$@")
while [ ${#todo[@]} -gt 0 ]; do
  rest=()
  for n in "${todo[@]}"; do
    if grep -q "] $n: 完了" $BASE/sens/run_round2.log; then
      pjsub -x NAMES=$n -L rscgrp=share-short -L elapse=01:00:00 -o $BASE/sens/eval_$n.out eval_job.sh
      echo "[$(date '+%F %T')] $n の評価を投入"
    elif grep -q "Error\] $n:" $BASE/sens/run_round2.log; then
      echo "[$(date '+%F %T')] $n は失敗したので評価しない"
    else
      rest+=("$n")
    fi
  done
  todo=("${rest[@]}")
  [ ${#todo[@]} -gt 0 ] && sleep 300
done
echo "===== [$(date '+%F %T')] eval_watch.sh 終了"
