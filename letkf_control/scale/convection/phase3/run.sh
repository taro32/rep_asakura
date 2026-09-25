#!/bin/sh
#--------------pjsub option-------------------
#PJM -L "rscgrp=debug-o"
#PJM -L "node=36"
#PJM --mpi "proc=144"
#PJM --omp "thread=12"
#PJM -L "elapse=00:30:00"
#PJM -g "gv42"
#PJM -j
#PJM -o "/work/gv42/v42013/20260923_enkc_convection/result/phase3_fcst1h/job.out"
#--------------------------------------------
# Phase 3: 1 member × 1 時間の単独予報（実行時間の計測）
# 投入: cd letkf_control/scale/convection/phase3 && pjsub run.sh
# 出力: /work/gv42/v42013/20260923_enkc_convection/result/phase3_fcst1h/
#   rep_asakura/run.sh と同じ環境設定・同じ実行ファイル（bin/scale-rm）を使う。

export SCALE_SYS="FX:700"
export SCALE_NETCDF_LIBS="-L/work/opt/local/aarch64/apps/fj/1.2.31/hdf5/1.12.0/lib -L/work/opt/local/aarch64/apps/fj/1.2.31/netcdf/4.7.4/lib  -lnetcdf -lnetcdff -lhdf5_hl -lhdf5_fortran -lhdf5 -lm -lz"
LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/work/opt/local/aarch64/apps/fj/1.2.31/hdf5/1.12.0/lib:/work/opt/local/aarch64/apps/fj/1.2.31/netcdf/4.7.4/lib:/work/opt/local/aarch64/apps/fj/1.2.31/netcdf-fortran/4.5.3/lib
export LD_LIBRARY_PATH
export SCALE_NETCDF_INCLUDE="-I//work/opt/local/aarch64/apps/fj/1.2.31/netcdf/4.7.4/include"

SCALE_RM=/work/02/gv42/v42013/scale-letkc/bin/scale-rm
CONF=/work/02/gv42/v42013/scale-letkc/letkf_control/scale/convection/phase3/run.conf
OUT=/work/gv42/v42013/20260923_enkc_convection/result/phase3_fcst1h
MEM=1   # member 番号（初期値は rep_asakura の 1/）

# 出力は種類ごと・member ごとに分ける: history/<MEM>/, refstate/<MEM>/, restart/<MEM>/
mkdir -p $OUT/history/$MEM $OUT/refstate/$MEM $OUT/restart/$MEM
cp $CONF $OUT/run.conf
cd $OUT

echo "start: $(date '+%Y-%m-%d %H:%M:%S')"
mpiexec $SCALE_RM run.conf
echo "exit status: $?"
echo "end:   $(date '+%Y-%m-%d %H:%M:%S')"
