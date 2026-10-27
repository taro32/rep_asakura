#!/bin/sh
#PJM -g gv42
#PJM -L rscgrp=share-short
#PJM -L gpu=1
#PJM -L elapse=01:00:00
#PJM -j
#===============================================================================
# B-2: スケールを分けた評価（analysis/check_scales.py）を Aquarius で実行する
#   pjsub -x GROUP=<組>,TRUTH=<真値の場所>,EXPS="<実験名> ..." [-L elapse=…] -o … sens/scales_job.sh
# 出力: docs/phase7d/sens/scales_<組>.out・.png・.npz
#===============================================================================
set -eu
CONV=/work/02/gv42/v42013/scale-letkc/letkf_control/scale/convection
export STIME=20000131000000 FIGDIR=$CONV/docs/phase7d/sens MPLCONFIGDIR=/tmp/mpl_$$
cd $CONV/analysis
echo "[$(date '+%F %T')] 開始（$(hostname)）: $GROUP $TRUTH $EXPS"
/work/02/gv42/v42013/miniconda3/bin/python3 check_scales.py $GROUP $TRUTH $EXPS > $FIGDIR/scales_$GROUP.out 2>&1
echo "[$(date '+%F %T')] 終了"
