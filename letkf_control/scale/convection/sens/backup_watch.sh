#!/bin/bash
#===============================================================================
# 予備の見張り（2026-10-16、wisteria03）。NoDA・M80・M80L10 のジョブが終わったあと、wisteria06 の tmux（run_m80.sh・noda）
# が評価を投げていなければ、代わりに成否を確かめて評価を投げる。NoDA は評価のあと、同化なしを足した比較図も作る。
# 記録: /work/gv42/v42013/20260923_enkc_convection/sens/backup_watch.log
#===============================================================================
cd "$(dirname "$0")"
BASE=/work/gv42/v42013/20260923_enkc_convection
TMPD=/work/02/gv42/v42013/scale-letkc/letkf_control/scale/tmp
PY=/work/02/gv42/v42013/miniconda3/bin/python3
exec >> $BASE/sens/backup_watch.log 2>&1
echo "===== [$(date '+%F %T')] backup_watch.sh 開始（$(hostname)）"
declare -A JOB=([NoDA]=9960864 [M80]=9960956 [M80L10]=9960974)
declare -A RUNLOG=([NoDA]=$BASE/sens/run_noda.log [M80]=$BASE/sens/run_m80.log [M80L10]=$BASE/sens/run_m80.log)
todo="NoDA M80 M80L10"
while [ -n "$todo" ]; do
  rest=""
  for n in $todo; do
    if pjstat 2>/dev/null | grep -q "^${JOB[$n]} "; then rest="$rest $n"; continue; fi
    sleep 600                                   # wisteria06 側が history を消して評価を投げる時間を待つ
    if grep -q "$n の評価を投入" ${RUNLOG[$n]}; then
      echo "[$(date '+%F %T')] $n: wisteria06 側が評価を投入済み"
    else
      nok=$(grep -c "SCALE-LETKF successfully completed" $TMPD/convection_$n/cycle_job.sh.${JOB[$n]}.out 2>/dev/null || true)
      if [ "$nok" = 6 ]; then
        rm -rf $BASE/sens/$n/*/hist/0[0-9][0-9][0-9]
        pjsub -x NAMES=$n -L rscgrp=share-short -L elapse=01:00:00 -o $BASE/sens/eval_$n.out eval_job.sh
        echo "[$(date '+%F %T')] $n: 6 cycle 正常終了。history を消して評価を投入（予備の見張りから）"
      else
        echo "[$(date '+%F %T')] $n: 正常に終わった cycle が $nok / 6。評価しない"
        continue
      fi
    fi
    if [ $n = NoDA ]; then
      until grep -q "NoDA: check_obspoint.py 終了" $BASE/sens/eval_NoDA.out 2>/dev/null; do sleep 120; done
      cd ../analysis
      $PY - > ../docs/phase7d/sens/NoDA/noda_increment.out 2>&1 <<'EOP'
import numpy as np, common as cm
B = "/work/gv42/v42013/20260923_enkc_convection/sens/NoDA"
for t in ["20000131010000", "20000131060000"]:
    g = cm.physical(cm.read_restart(f"{B}/{t}/" + ("gues_letkf/mean" if t != "20000131060000" else "gues/mean"), t))
    a = cm.physical(cm.read_restart(f"{B}/{t}/anal/mean", t))
    print(t, "解析 − 第一推定 の最大絶対値: " + "  ".join(f"{k.split()[0]} {np.abs(a[k] - g[k]).max():.2e}" for k in g))
EOP
      $PY compare_sens.py noda > ../docs/phase7d/sens/compare_sens_noda.out 2>&1
      cd ../sens
      echo "[$(date '+%F %T')] NoDA: 同化していないことの確認（docs/phase7d/sens/NoDA/noda_increment.out）と比較図（compare_grid_noda.png）を作成"
    fi
  done
  todo=$rest
  [ -n "$todo" ] && sleep 120
done
echo "===== [$(date '+%F %T')] backup_watch.sh 終了"
