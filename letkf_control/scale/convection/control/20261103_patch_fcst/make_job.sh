#!/bin/sh
#PJM -g gv42
#PJM -L rscgrp=share-short
#PJM -L gpu=1
#PJM -L elapse=01:00:00
#PJM -j
#===============================================================================
# 制御: パッチ型の摂動を入れたアンサンブル予報の入力を作る（make_patch_fcst.py。Aquarius）
#   pjsub -x NAME=phase9_patch_t08,HOURS=10 -o <ログ> control/20261103_patch_fcst/make_job.sh
#===============================================================================
set -eu
cd /work/02/gv42/v42013/scale-letkc/letkf_control/scale/convection/control/20261103_patch_fcst
echo "[$(date '+%F %T')] 開始"
NAME=$NAME HOURS=$HOURS /work/02/gv42/v42013/miniconda3/bin/python3 make_patch_fcst.py 80
echo "[$(date '+%F %T')] 終了"
