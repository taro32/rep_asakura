#!/bin/sh
#PJM -g gv42
#PJM -L rscgrp=debug-o
#PJM -L node=36
#PJM --mpi proc=144
#PJM --omp thread=12
#PJM -L elapse=00:30:00
#PJM -j
#===============================================================================
# 制御: パッチ型の摂動を入れたアンサンブル予報（make_patch_fcst.py で作った入力を scale-rm_ens で流す。Wisteria）
#   試験:  pjsub -x OUT=<出力> -o <ログ> control/20261103_patch_fcst/run_fcst.sh
#   本番:  pjsub -L rscgrp=regular-o,node=324,elapse=02:00:00 --mpi proc=1296 -x OUT=<出力> -o <ログ> control/20261103_patch_fcst/run_fcst.sh
#   ノード数 ÷ 36 本ずつ同時に流し、残りは順に流す（scale-rm_ens が自動で分ける）
#===============================================================================
export SCALE_SYS="FX700"
LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/work/opt/local/aarch64/apps/fj/1.2.31/hdf5/1.12.0/lib:/work/opt/local/aarch64/apps/fj/1.2.31/netcdf/4.7.4/lib:/work/opt/local/aarch64/apps/fj/1.2.31/netcdf-fortran/4.5.3/lib
export LD_LIBRARY_PATH

ENSMODEL=/work/02/gv42/v42013/scale-letkc/letkf_control/scale/ensmodel/scale-rm_ens   # Phase 8 の cycle と同じ実行ファイル
cd $OUT/work || exit 1
cp $ENSMODEL ./scale-rm_ens
echo "[$(date '+%F %T')] 開始"
mpiexec ./scale-rm_ens launcher.conf    # プロセス数は --mpi proc のとおり
res=$?
echo "[$(date '+%F %T')] 終了（exit status: $res）"
exit $res
