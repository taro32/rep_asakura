#!/bin/sh
#PJM -g gv42
#PJM -L rscgrp=share-short
#PJM -L gpu=1
#PJM -L elapse=02:00:00
#PJM -j
#===============================================================================
# 制御: 土壌水分の動き（層ごとの値、member 間のばらつき、水の収支。80 member、result_m80。Aquarius）
#   pjsub -o <ログ> analysis/control/20261102_soil_cov/plot_soil_track_job.sh
# 出力: docs/control/20261102_soil_track/soil_track_target.png・soil_track_spread.png・soil_budget.png・soil_track.npz・soil_track.out
#===============================================================================
set -eu
CONV=/work/02/gv42/v42013/scale-letkc/letkf_control/scale/convection
export STIME=20000131000000
export OUTDIR=/work/gv42/v42013/20260923_enkc_convection/result_m80
export FIGDIR=$CONV/docs/control/20261102_soil_track
export MPLCONFIGDIR=/tmp/mpl_$$     # 計算ノードの /pjmhome には書けないため
cd $CONV/analysis
echo "[$(date '+%F %T')] 開始"
/work/02/gv42/v42013/miniconda3/bin/python3 control/20261102_soil_cov/plot_soil_track.py 24 80 > $FIGDIR/soil_track.out 2>&1
echo "[$(date '+%F %T')] 終了"
