#!/bin/sh
#--------------pjsub option-------------------
#PJM -L "rscgrp=regular-o"
#PJM -L "node=36"
#PJM --mpi "proc=144"
#PJM --omp "thread=12"
#PJM -L "elapse=10:00:00"
#PJM -g "gv42"
#PJM -j
#--------------------------------------------
# Phase 7d: 30 日スピンアップ（浅倉さんの論文の設計に倣う。格子は 2 km）
#   1. 摂動なしの初期値を 1 本作る（init/init.conf_base + 摂動なしのサウンディング env.txt。温位の乱数 RANDOM_THETA は 1 通り）
#   2. 2000-01-01 00:00 から 30 日積分し、restart_20000131-000000.000 を作る（10 日ごとにも出る）
# このあと init/perturb_soil.py で、20000131 の restart の土壌水分（最上層）に member ごとの摂動を入れる。
#
# 投入: cd letkf_control/scale/convection/spinup && pjsub run.sh
# 出力: /work/gv42/v42013/20260923_enkc_convection/spinup_20261003/
# 見込み: 1 時間の予報が 21 秒（Phase 3）なので、30 日 = 720 時間で約 4.2 時間。
export SCALE_SYS="FX700"
export SCALE_NETCDF_LIBS="-L/work/opt/local/aarch64/apps/fj/1.2.31/hdf5/1.12.0/lib -L/work/opt/local/aarch64/apps/fj/1.2.31/netcdf/4.7.4/lib  -lnetcdf -lnetcdff -lhdf5_hl -lhdf5_fortran -lhdf5 -lm -lz"
LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/work/opt/local/aarch64/apps/fj/1.2.31/hdf5/1.12.0/lib:/work/opt/local/aarch64/apps/fj/1.2.31/netcdf/4.7.4/lib:/work/opt/local/aarch64/apps/fj/1.2.31/netcdf-fortran/4.5.3/lib
export LD_LIBRARY_PATH
export SCALE_NETCDF_INCLUDE="-I//work/opt/local/aarch64/apps/fj/1.2.31/netcdf/4.7.4/include"

BIN=/work/02/gv42/v42013/scale-letkc/bin
CONV=/work/02/gv42/v42013/scale-letkc/letkf_control/scale/convection
OUT=/work/gv42/v42013/20260923_enkc_convection/spinup_20261003
NPE=144

if [ -n "$(ls -A $OUT/restart 2>/dev/null)" ]; then
  echo "[Error] $OUT/restart にすでにファイルがあります。上書きしないので止めます。" >&2
  exit 1
fi
mkdir -p $OUT/init $OUT/restart $OUT/refstate $OUT/history
cp $CONV/spinup/run.conf $OUT/run.conf
cp $CONV/init/ensperturb/env.txt $OUT/init/env.txt

# 1. 摂動なしの初期値（init/ensinit.sh と同じ置き換え。サウンディングだけ env.txt）
sed -e "/!--ENV_IN_SOUNDING_file--/a ENV_IN_SOUNDING_file = \"$OUT/init/env.txt\"," \
    -e "s#\"\.\./\(param\.bucket\.conf\|PARAG\.29\|PARAPC\.29\|VARDATA\.RM29\|cira\.nc\|MIPAS\)\"#\"$CONV/dat/\1\"#" \
    $CONV/init/init.conf_base > $OUT/init/init.conf
cd $OUT/init
echo "[$(date '+%F %T')] init start"
mpiexec $BIN/scale-rm_init ./init.conf
n=$(ls init_20000101-000000.000.pe*.nc 2>/dev/null | wc -l)
if [ "$n" -ne $NPE ]; then
  echo "[Error] 初期値のファイルが $n 個です（$NPE 個必要）。" >&2
  exit 1
fi
echo "[$(date '+%F %T')] init done"

# 2. 30 日積分
cd $OUT
echo "[$(date '+%F %T')] run start"
mpiexec $BIN/scale-rm run.conf
echo "[$(date '+%F %T')] run end (exit $?)"
n=$(ls restart/restart_20000131-000000.000.pe*.nc 2>/dev/null | wc -l)
if [ "$n" -ne $NPE ]; then
  echo "[Error] 20000131 の restart が $n 個です（$NPE 個必要）。" >&2
  exit 1
fi
md5sum restart/restart_20000131-000000.000.pe*.nc > restart_20000131.md5
chmod a-w restart/restart_20000131-000000.000.pe*.nc
echo "[$(date '+%F %T')] all done"
