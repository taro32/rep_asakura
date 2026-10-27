#!/bin/sh
#PJM -g gv42
#PJM -L rscgrp=share-short
#PJM -L gpu=1
#PJM -L elapse=01:00:00
#PJM -j
#===============================================================================
# 感度実験 1 本の評価（Aquarius。解析の Python は x86_64 なので Odyssey では動かない）
#   pjsub -x NAMES="<実験名> [<実験名> …]" [-L rscgrp=share-debug] sens/eval_job.sh（並べた実験を順に評価する）
# 出力: docs/phase7d/sens/<実験名>/（check_cycles_fast.out・check_obspoint.out・図）
#===============================================================================
set -eu
CONV=/work/02/gv42/v42013/scale-letkc/letkf_control/scale/convection
BASE=/work/gv42/v42013/20260923_enkc_convection
PY=/work/02/gv42/v42013/miniconda3/bin/python3
export STIME=20000131000000
export MPLCONFIGDIR=/tmp/mpl_$$     # 計算ノードの /pjmhome には書けないため
cd $CONV/analysis
for NAME in ${NAMES:-$NAME}; do
  export OUTDIR=$BASE/sens/$NAME TRUTHDIR=$BASE/result
  P=$OUTDIR/sens_params.txt
  export LCYCLE=$(sed -n 's/^LCYCLE=//p' $P); LCYCLE=${LCYCLE:-3600}
  if grep -q "^OBS=.*obsmake: 1" $P; then export TRUTHDIR=$OUTDIR; fi   # 自分の観測を作った実験は、自分の mdet が真値
  T=$(sed -n 's/^TRUTHDIR=//p' $P); if [ -n "$T" ]; then export TRUTHDIR=$T; fi   # 指定があればそれ（長い実験は TRUTH24 の真値・観測）
  echo "[$(date '+%F %T')] $NAME: LCYCLE=$LCYCLE TRUTHDIR=$TRUTHDIR"
  export FIGDIR=$CONV/docs/phase7d/sens/$NAME
  mkdir -p $FIGDIR
  echo "[$(date '+%F %T')] $NAME: 開始（$(hostname)、$(uname -m)）"
  $PY check_cycles.py --fast > $FIGDIR/check_cycles_fast.out 2>&1
  echo "[$(date '+%F %T')] $NAME: check_cycles.py 終了"
  $PY check_obspoint.py > $FIGDIR/check_obspoint.out 2>&1
  echo "[$(date '+%F %T')] $NAME: check_obspoint.py 終了"
done
