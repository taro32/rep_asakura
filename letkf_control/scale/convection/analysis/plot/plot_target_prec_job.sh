#!/bin/sh
#PJM -g gv42
#PJM -L rscgrp=share-short
#PJM -L gpu=1
#PJM -L elapse=00:30:00
#PJM -j
#===============================================================================
# Phase 9: 制御の目標領域（x = 80 km・y = 120 km の 20 km 四方）の降水の時間変化（80 member、result_m80。Aquarius）
#   pjsub -o <ログ> analysis/plot/plot_target_prec_job.sh
# 出力: docs/phase9/target_prec/target_prec.png・.npz・target_prec.out
#===============================================================================
set -eu
CONV=/work/02/gv42/v42013/scale-letkc/letkf_control/scale/convection
export STIME=20000131000000
export OUTDIR=/work/gv42/v42013/20260923_enkc_convection/result_m80
export FIGDIR=$CONV/docs/phase9/target_prec
export MPLCONFIGDIR=/tmp/mpl_$$     # 計算ノードの /pjmhome には書けないため
cd $CONV/analysis
echo "[$(date '+%F %T')] 開始"
/work/02/gv42/v42013/miniconda3/bin/python3 plot/plot_target_prec.py 24 80 > $FIGDIR/target_prec.out 2>&1
echo "[$(date '+%F %T')] 終了"
