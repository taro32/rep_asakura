#!/bin/sh
#PJM -g gv42
#PJM -L rscgrp=share-short
#PJM -L gpu=1
#PJM -L elapse=02:00:00
#PJM -j
#===============================================================================
# Phase 8 の 24 時間（80 member、result_m80）の、member ごとの積算降水の図（Aquarius。解析の Python は x86_64）
#   pjsub -o <ログ> analysis/plot_member_prec_job.sh            （既定: 12〜24 時間）
#   pjsub -x H0=6,H1=12 -o <ログ> analysis/plot_member_prec_job.sh
# 出力: docs/phase8/run24_m80/member_prec_<H0>-<H1>h.png・_sorted.png・.npz
#===============================================================================
set -eu
CONV=/work/02/gv42/v42013/scale-letkc/letkf_control/scale/convection
export STIME=20000131000000
export OUTDIR=/work/gv42/v42013/20260923_enkc_convection/result_m80
export FIGDIR=$CONV/docs/phase8/run24_m80
export MPLCONFIGDIR=/tmp/mpl_$$     # 計算ノードの /pjmhome には書けないため
cd $CONV/analysis
echo "[$(date '+%F %T')] 開始"
/work/02/gv42/v42013/miniconda3/bin/python3 plot_member_prec.py ${H0:-12} ${H1:-24} 80
echo "[$(date '+%F %T')] 終了"
