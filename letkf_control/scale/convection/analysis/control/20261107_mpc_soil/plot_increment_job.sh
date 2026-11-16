#!/bin/sh
#PJM -g gv42
#PJM -L rscgrp=share-short
#PJM -L gpu=1
#PJM -L elapse=00:40:00
#PJM -j
#===============================================================================
# MPC の制御の増分（LAND_WATER、anal − gues）の地図と量の図（Aquarius。解析の Python は x86_64）
#   pjsub -o <ログ> analysis/control/20261107_mpc_soil/plot_increment_job.sh
#   pjsub -x RUNS="r080 p3_tc1" -o <ログ> analysis/control/20261107_mpc_soil/plot_increment_job.sh
# 出力: docs/control/20261107_mpc_soil/increment_<実験名>.png・increment_amount.png
#       読んだ値は mpc_soil/increment_cache/increment_<実験名>.npz（次からはこれを使う。元を直したら消す）
#===============================================================================
set -eu
CONV=/work/02/gv42/v42013/scale-letkc/letkf_control/scale/convection
export FIGDIR=$CONV/docs/control/20261107_mpc_soil
export CACHE=/work/gv42/v42013/20260923_enkc_convection/mpc_soil/increment_cache
export MPLCONFIGDIR=/tmp/mpl_$$     # 計算ノードの /pjmhome には書けないため
cd $CONV/analysis
echo "[$(date '+%F %T')] 開始"
/work/02/gv42/v42013/miniconda3/bin/python3 control/20261107_mpc_soil/plot_increment.py --runs ${RUNS:-r080 p3_tc1 p3_tc3}
echo "[$(date '+%F %T')] 終了"
