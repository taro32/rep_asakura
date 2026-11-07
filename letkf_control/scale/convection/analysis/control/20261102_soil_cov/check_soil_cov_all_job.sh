#!/bin/sh
#PJM -g gv42
#PJM -L rscgrp=share-short
#PJM -L gpu=1
#PJM -L elapse=01:00:00
#PJM -j
#===============================================================================
# 制御: 土壌水分と目標領域の雨の相関（0〜12 時のすべての時刻）（80 member、result_m80。Aquarius）
#   pjsub -o <ログ> analysis/control/20261102_soil_cov/check_soil_cov_all_job.sh
# 出力: docs/control/20261103_soil_cov_all/soil_cov_all_summary.png・soil_corr_all_S20.png・soil_cov_all.npz・soil_cov_all.out
#===============================================================================
set -eu
CONV=/work/02/gv42/v42013/scale-letkc/letkf_control/scale/convection
export STIME=20000131000000
export OUTDIR=/work/gv42/v42013/20260923_enkc_convection/result_m80
export FIGDIR=$CONV/docs/control/20261103_soil_cov_all
export MPLCONFIGDIR=/tmp/mpl_$$     # 計算ノードの /pjmhome には書けないため
cd $CONV/analysis
echo "[$(date '+%F %T')] 開始"
/work/02/gv42/v42013/miniconda3/bin/python3 control/20261102_soil_cov/check_soil_cov_all.py 80 > $FIGDIR/soil_cov_all.out 2>&1
echo "[$(date '+%F %T')] 終了"
