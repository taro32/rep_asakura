#!/bin/bash
#===============================================================================
# 感度実験 7 本を順に流す（tmux の中で動かす。Claude のセッションが切れても進む）
#   1. Cp（基準の再現）。1 cycle 目の obsdep を基準（ジョブ 9844986）と比べて記録する
#   2. 残りの 6 本を 2 本ずつ（Odyssey の上限 2,304 ノード ÷ 792）
# 記録: /work/gv42/v42013/20260923_enkc_convection/sens/run_all.log
# 注意: 2026-10-15 の実行の記録。このあと submit.sh の引数を KEY=値 の形に変えたので、このままでは動かない
#===============================================================================
cd "$(dirname "$0")"
BASE=/work/gv42/v42013/20260923_enkc_convection
LOG=$BASE/sens/run_all.log
mkdir -p $BASE/sens
exec >> $LOG 2>&1
echo "===== [$(date '+%F %T')] run_all.sh 開始（$(hostname)）"

./submit.sh Cp 2.0D4 1.45D0 0.8D0 || { echo "[$(date '+%F %T')] Cp が失敗したので止める"; exit 1; }
for t in 20000131010000 20000131060000; do
  if cmp -s $BASE/result/obsdep/obsdep_$t.dat $BASE/sens/Cp/obsdep/obsdep_$t.dat; then
    echo "[$(date '+%F %T')] Cp の obsdep_$t は基準と完全に一致"
  else
    echo "[$(date '+%F %T')] Cp の obsdep_$t は基準と一致しない（続ける。あとで差を調べる）"
  fi
done

for pair in "L10 1.0D4 1.45D0 0.8D0|L50 5.0D4 1.45D0 0.8D0" \
            "I10 2.0D4 1.0D0 0.8D0|I20 2.0D4 2.0D0 0.8D0" \
            "R00 2.0D4 1.45D0 0.0D0|R05 2.0D4 1.45D0 0.5D0"; do
  IFS='|' read -r a b <<< "$pair"
  ./submit.sh $a & pa=$!
  sleep 60                                   # 投入の処理（tmp の準備）が重ならないように少しずらす
  ./submit.sh $b & pb=$!
  wait $pa || echo "[$(date '+%F %T')] ${a%% *} が失敗"
  wait $pb || echo "[$(date '+%F %T')] ${b%% *} が失敗"
done
echo "===== [$(date '+%F %T')] run_all.sh 終了"
