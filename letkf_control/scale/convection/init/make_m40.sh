#!/bin/sh
#PJM -g gv42
#PJM -L rscgrp=share-debug
#PJM -L gpu=1
#PJM -L elapse=00:30:00
#PJM -j
#===============================================================================
# 40 member の初期値（Phase 7d の感度実験 M40）を作る。Aquarius で実行する（解析の Python は x86_64）
#   pjsub -o /work/gv42/v42013/20260923_enkc_convection/init_soil_m40.out init/make_m40.sh
# - 1〜20 番と mdet は init_soil_20261003 の 1〜20・21 をそのまま使う（ディレクトリへのリンク。mdet は 41 番として置く）
# - 21〜40 番は perturb_soil.py で新しく作る（種 SEED + 22〜41）
# - md5.txt: 元の記録の 1〜20 番と 21 番（→ 41 番に読み替え）に、新しい 21〜40 番の記録を足す
# 取り込み: NMEM=40 MDET_SRC=41 STIME=20000131000000 SRC=…/init_soil_m40 MD5_LIST=…/init_soil_m40/md5.txt import_rep_asakura.sh <OUTDIR>
#===============================================================================
set -eu
BASE=/work/gv42/v42013/20260923_enkc_convection
OLD=$BASE/init_soil_20261003
GEN=$BASE/init_soil_m40
PY=/work/02/gv42/v42013/miniconda3/bin/python3
mkdir -p $GEN
for m in $(seq 1 20); do ln -sfn $OLD/$m $GEN/$m; done
ln -sfn $OLD/21 $GEN/41
cd /work/02/gv42/v42013/scale-letkc/letkf_control/scale/convection/init
GEN=$GEN M_FIRST=21 M_LAST=40 SEED_SHIFT=1 $PY perturb_soil.py
{ grep -E " ([1-9]|1[0-9]|20)/" $OLD/md5.txt; grep " 21/" $OLD/md5.txt | sed "s| 21/| 41/|"; cat $GEN/md5_new.txt; } > $GEN/md5.txt
echo "md5.txt: $(wc -l < $GEN/md5.txt) 行（41 × 144 = 5904 行のはず）"
