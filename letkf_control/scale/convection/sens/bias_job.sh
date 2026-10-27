#!/bin/sh
#PJM -g gv42
#PJM -L rscgrp=share-short
#PJM -L gpu=1
#PJM -L elapse=01:30:00
#PJM -j
# 偏りの確認（analysis/check_bias.py）を Aquarius で実行する。pjsub -x TRUTH=…,EXPS="名前=場所 …",OUT=… sens/bias_job.sh
set -eu
cd /work/02/gv42/v42013/scale-letkc/letkf_control/scale/convection/analysis
STIME=20000131000000 /work/02/gv42/v42013/miniconda3/bin/python3 check_bias.py $TRUTH $EXPS > $OUT 2>&1
