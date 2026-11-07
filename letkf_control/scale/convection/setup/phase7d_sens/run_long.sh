#!/bin/bash
#===============================================================================
# B-1（2026-10-16）: 24 時間回して、誤差が横ばいになる高さを同化あり・なしで比べる（計画書の Phase 7d「終了の基準」の案）
#   TRUTH24:  基準の設定（20 member・20 km）で 24 時間。obsmake で 24 時間分の観測を作り、その mdet を真値にする
#   M80L10_24: 80 member・10 km（いちばん良かった設定）。TRUTH24 の観測を読む
#   NoDA24:   同化なし。TRUTH24 の観測の観測誤差を 1.0e5 にしたものを読む（INFL_MUL 1.0・RELAX_ALPHA 0.0）
# どれも HIST_CLEAN=1（各 cycle の後に member の history・restart を消す）。終わったら評価（eval_job.sh、2 時間）を投げる。
# 記録: /work/gv42/v42013/20260923_enkc_convection/sens/run_long.log
#===============================================================================
cd "$(dirname "$0")"
BASE=/work/gv42/v42013/20260923_enkc_convection
LAST=20000201000000
PY=/work/02/gv42/v42013/miniconda3/bin/python3
exec >> $BASE/sens/run_long.log 2>&1
echo "===== [$(date '+%F %T')] run_long.sh 開始（$(hostname)）"
evaluate() {
  pjsub -x NAMES=$1 -L rscgrp=share-short -L elapse=02:00:00 -o $BASE/sens/eval_$1.out eval_job.sh
  echo "[$(date '+%F %T')] $1 の評価を投入"
}
./submit.sh TRUTH24 OWN_OBS=1 LAST=$LAST HIST_CLEAN=1 TIME_LIMIT=06:00:00 || { echo "TRUTH24 が失敗したので止める"; exit 1; }
evaluate TRUTH24

# 同化なし用の観測（観測誤差だけ 1.0e5）
D=$BASE/sens_obs/NoDA24; mkdir -p $D
cp $BASE/sens/TRUTH24/obs/controltarget $D/
$PY - <<EOP
import glob, os, numpy as np
for f in sorted(glob.glob("$BASE/sens/TRUTH24/obs/obs_*.dat")):
    raw = np.fromfile(f, dtype="<i4").reshape(-1, 10)
    v = raw[:, 1:9].copy().view("<f4")
    v[:, 5] = 1.0e5
    raw[:, 1:9] = v.view("<i4")
    raw.tofile("$D/" + os.path.basename(f))
print("NoDA24 の観測:", len(glob.glob("$D/obs_*.dat")), "時刻")
EOP

./submit.sh M80L10_24 MEMBER=80 INIT=init_soil_m80 NNODES=1476 HORI_LOCAL=1.0D4 OBS_DIR=$BASE/sens/TRUTH24/obs TRUTHDIR=$BASE/sens/TRUTH24 \
            LAST=$LAST HIST_CLEAN=1 TIME_LIMIT=08:00:00 && evaluate M80L10_24 & p1=$!
sleep 120
./submit.sh NoDA24 OBS_DIR=$D INFL_MUL=1.0D0 RELAX_ALPHA=0.0D0 TRUTHDIR=$BASE/sens/TRUTH24 \
            LAST=$LAST HIST_CLEAN=1 TIME_LIMIT=06:00:00 && evaluate NoDA24 & p2=$!
wait $p1 || echo "[$(date '+%F %T')] M80L10_24 が失敗"
wait $p2 || echo "[$(date '+%F %T')] NoDA24 が失敗"
echo "===== [$(date '+%F %T')] run_long.sh 終了"
