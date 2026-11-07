#!/bin/sh
#PJM -g gv42
#PJM -L rscgrp=share-short
#PJM -L gpu=1
#PJM -L elapse=01:00:00
#PJM -j
#===============================================================================
# 制御: パッチ型の摂動の予報で、格子ごとのボーエン比の相関の地図（check_patch_bowen_map.py。Aquarius）
#   pjsub -x HOUR=10 -o <ログ> analysis/control/20261103_patch_fcst/check_patch_bowen_map_job.sh
# 出力: docs/control/20261103_patch_fcst/patch_bowen_map_<HOUR>.png・.npz・.out
#===============================================================================
set -eu
CONV=/work/02/gv42/v42013/scale-letkc/letkf_control/scale/convection
export FIGDIR=$CONV/docs/control/20261103_patch_fcst
export HOUR=${HOUR:-10}
export MPLCONFIGDIR=/tmp/mpl_$$     # 計算ノードの /pjmhome には書けないため
cd $CONV/analysis
echo "[$(date '+%F %T')] 開始"
/work/02/gv42/v42013/miniconda3/bin/python3 control/20261103_patch_fcst/check_patch_bowen_map.py > $FIGDIR/patch_bowen_map_$HOUR.out 2>&1
echo "[$(date '+%F %T')] 終了"
