#!/bin/sh
#PJM -g gv42
#PJM -L rscgrp=share-debug
#PJM -L gpu=1
#PJM -L elapse=00:30:00
#PJM -j
#===============================================================================
# 80 member の初期値（Phase 7d の感度実験 M80）を作る。Aquarius で実行する（解析の Python は x86_64）
#   pjsub -o /work/gv42/v42013/20260923_enkc_convection/init_soil_m80.out init/make_m80.sh
# - 1〜40 番と mdet は init_soil_m40 の 1〜40・41 をそのまま使う（リンク。mdet は 81 番として置く）。1〜40 番は M40 と同じ
# - 41〜80 番は perturb_soil.py で新しく作る（種 SEED + 42〜81）
# - md5.txt: init_soil_m40 の記録の 1〜40 番と 41 番（→ 81 番に読み替え）に、新しい 41〜80 番の記録を足す
# 取り込み: NMEM=80 MDET_SRC=81 STIME=20000131000000 SRC=…/init_soil_m80 MD5_LIST=…/init_soil_m80/md5.txt import_rep_asakura.sh <OUTDIR>
#===============================================================================
set -eu
BASE=/work/gv42/v42013/20260923_enkc_convection
OLD=$BASE/init_soil_m40
GEN=$BASE/init_soil_m80
PY=/work/02/gv42/v42013/miniconda3/bin/python3
mkdir -p $GEN
for m in $(seq 1 40); do ln -sfn $(readlink -f $OLD/$m) $GEN/$m; done
ln -sfn $(readlink -f $OLD/41) $GEN/81
cd /work/02/gv42/v42013/scale-letkc/letkf_control/scale/convection/init
GEN=$GEN M_FIRST=41 M_LAST=80 SEED_SHIFT=1 $PY perturb_soil.py
{ grep -E " ([1-9]|[1-3][0-9]|40)/" $OLD/md5.txt; grep " 41/" $OLD/md5.txt | sed "s| 41/| 81/|"; cat $GEN/md5_new.txt; } > $GEN/md5.txt
echo "md5.txt: $(wc -l < $GEN/md5.txt) 行（81 × 144 = 11664 行のはず）"
