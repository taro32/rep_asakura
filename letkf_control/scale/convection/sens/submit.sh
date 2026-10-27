#!/bin/bash
#===============================================================================
# 感度実験 1 本を投入する（Phase 7d「同化の精度の確認」。計画書の「感度実験」）
#
# 使い方: sens/submit.sh <実験名> [KEY=値 ...]
#   例:   sens/submit.sh L10 HORI_LOCAL=1.0D4
#         sens/submit.sh M40 MEMBER=40 INIT=init_soil_m40 TIME_LIMIT=03:00:00
#         sens/submit.sh T15 LCYCLE=900 LTIMESLOT=300 FCSTOUT=300 OWN_OBS=1 TIME_LIMIT=06:00:00
#   KEY（省略すると基準 9844986 と同じ）:
#     HORI_LOCAL・INFL_MUL・RELAX_ALPHA・GROSS_ERROR  LETKF の値（Fortran の書き方。config.nml.letkf に入る）
#     MEMBER                                          member 数（既定 20）
#     INIT                                            初期値（既定 init_soil_20261003。40 member は init_soil_m40）
#     LCYCLE・LTIMESLOT・FCSTOUT                       同化の間隔・スロット・history の間隔 [s]（既定 3600・600・600）
#     OWN_OBS=1                                       obsmake を走らせて自分の観測を作る（同化の間隔を変えるとき。
#                                                     既定 0 = 基準の観測 result/obs を読む）
#     NNODES                                          ノード数（既定 (MEMBER+2) × 36。減らすと member を何回かに分けて流す。80 member は 1476）
#     PPN・THREADS                                    1 ノードのプロセス数・スレッド数（既定 4・12。実行ファイルがスレッド 12 に固定なので変えられない）
#     START_FROM・START_TIME                          初期値を別の実験の解析から取る（例: Cp・20000131050000。1 点観測試験用）
#     LAST                                            最後の解析時刻（既定 20000131060000）
#     HIST_CLEAN=1                                    各 cycle の LETKF の後に member の history を消す（長い実験用）
#     TRUTHDIR                                        評価に使う真値・観測の場所（記録だけ。eval_job.sh が読む。既定は観測の作り方から決まる）
#     TIME_LIMIT                                      ジョブの上限（既定 01:30:00）
#
# - 結果: /work/gv42/v42013/20260923_enkc_convection/sens/<実験名>/（使った設定は sens_params.txt）
# - 作業ディレクトリ: letkf_control/scale/tmp/convection_<実験名>（同時に走らせても混ざらない）
# - 期間は 6 時間（1/31 00 時開始）。cycle_run.sh はジョブが終わるまで待つ。終わったら member の history を消す
#===============================================================================
set -eu
cd "$(dirname "$0")/.."                      # convection/

NAME=$1; shift
HORI_LOCAL=; INFL_MUL=; RELAX_ALPHA=; GROSS_ERROR=
MEMBER=20; INIT=init_soil_20261003; LCYCLE=3600; LTIMESLOT=600; FCSTOUT=600; OWN_OBS=0; TIME_LIMIT=01:30:00
HIST_CLEAN=0; TRUTHDIR=; NNODES=; PPN=4; THREADS=12; START_FROM=; START_TIME=20000131000000; LAST=20000131060000; OBS_DIR=
for kv in "$@"; do
  case ${kv%%=*} in
    HORI_LOCAL|INFL_MUL|RELAX_ALPHA|GROSS_ERROR|MEMBER|INIT|LCYCLE|LTIMESLOT|FCSTOUT|OWN_OBS|TIME_LIMIT|HIST_CLEAN|TRUTHDIR|NNODES|PPN|THREADS|START_FROM|START_TIME|LAST|OBS_DIR) eval "${kv%%=*}=\"${kv#*=}\"" ;;
    *) echo "[Error] 知らない設定: $kv" >&2; exit 1 ;;
  esac
done

BASE=/work/gv42/v42013/20260923_enkc_convection
OUT=$BASE/sens/$NAME
SRC=$BASE/$INIT
STIME=$START_TIME
ETIME=$(date -u -d "${LAST:0:8} ${LAST:8:2}:${LAST:10:2}:${LAST:12:2} $LCYCLE seconds ago" +%Y%m%d%H%M%S)   # 最後の cycle の開始時刻

if [ -e $OUT/$STIME ]; then
  echo "[Error] $OUT/$STIME がすでにあります。" >&2
  exit 1
fi
mkdir -p $OUT
if [ -n "$START_FROM" ]; then
  # 別の実験の解析（$START_TIME）から始める。anal/ は LETKC・LETKF がその場で上書きするのでコピーする
  mkdir -p $OUT/$STIME
  cp -r $BASE/sens/$START_FROM/$STIME/anal $OUT/$STIME/
  echo "初期値: $BASE/sens/$START_FROM/$STIME/anal をコピー"
else
  (cd init && NMEM=$MEMBER MDET_SRC=$((MEMBER + 1)) STIME=$STIME SRC=$SRC MD5_LIST=$SRC/md5.txt ./import_rep_asakura.sh $OUT)
fi

if [ -n "$OBS_DIR" ]; then
  export SENS_OBS=$OBS_DIR SENS_OBSMAKE_RUN=0     # 用意した観測（1 点観測試験）
elif [ "$OWN_OBS" = 1 ]; then
  mkdir -p $OUT/obs
  cp $BASE/result/obs/controltarget $OUT/obs/   # LETKC の目標（制御なし）
  export SENS_OBS=$OUT/obs SENS_OBSMAKE_RUN=1
else
  export SENS_OBS=$BASE/result/obs SENS_OBSMAKE_RUN=0
fi
export SENS_OUTDIR=$OUT SENS_TMPSUBDIR=convection_$NAME
export SENS_MEMBER=$MEMBER SENS_LCYCLE=$LCYCLE SENS_LTIMESLOT=$LTIMESLOT SENS_FCSTOUT=$FCSTOUT SENS_PPN=$PPN SENS_THREADS=$THREADS
if [ -n "$NNODES" ]; then export SENS_NNODES=$NNODES; fi
export SENS_HIST_CLEAN=$HIST_CLEAN
for v in HORI_LOCAL INFL_MUL RELAX_ALPHA GROSS_ERROR; do
  if [ -n "${!v}" ]; then export SENS_$v="${!v}"; fi
done
cat > $OUT/sens_params.txt <<EOT
name=$NAME
HORI_LOCAL=${HORI_LOCAL:-（基準: 2.0D4）}
INFL_MUL=${INFL_MUL:-（基準: 1.45D0）}
RELAX_ALPHA=${RELAX_ALPHA:-（基準: 0.8D0）}
GROSS_ERROR=${GROSS_ERROR:-（基準: 5.0D0）}
MEMBER=$MEMBER
NNODES=${NNODES:-（既定）}
PPN=$PPN
THREADS=$THREADS
INIT=$( [ -n "$START_FROM" ] && echo "sens/$START_FROM/$STIME/anal" || echo "$SRC" )
LCYCLE=$LCYCLE
LTIMESLOT=$LTIMESLOT
FCSTOUT=$FCSTOUT
OBS=$SENS_OBS（obsmake: $SENS_OBSMAKE_RUN）
STIME=$STIME
ETIME=$ETIME
LAST=$LAST
HIST_CLEAN=$HIST_CLEAN
${TRUTHDIR:+TRUTHDIR=$TRUTHDIR}
submitted=$(date '+%Y-%m-%d %H:%M:%S')
EOT

echo "[$(date '+%F %T')] $NAME: cycle_run.sh を開始"
./cycle_run.sh $STIME $ETIME 1 10 static $TIME_LIMIT > $OUT/cycle_run.log 2>&1 || { echo "[Error] $NAME: cycle_run.sh が失敗（$OUT/cycle_run.log）" >&2; exit 1; }

# すべての cycle が正常に終わったか（出力のディレクトリは投入のときに先に作られるので、ジョブのログで確かめる）
jobid=$(grep -o "Job [0-9]* submitted" $OUT/cycle_run.log | awk '{print $2}')
jobout=../tmp/convection_$NAME/cycle_job.sh.$jobid.out
ncyc=$(( ( $(date -u -d "${LAST:0:8} ${LAST:8:2}:${LAST:10:2}" +%s) - $(date -u -d "${STIME:0:8} ${STIME:8:2}:${STIME:10:2}" +%s) ) / LCYCLE ))
nok=$(grep -c "SCALE-LETKF successfully completed" $jobout 2>/dev/null || true)
if [ "$nok" != "$ncyc" ]; then
  echo "[Error] $NAME: 正常に終わった cycle が $nok / $ncyc（$jobout）" >&2
  exit 1
fi
rm -rf $OUT/*/hist/0[0-9][0-9][0-9]
echo "[$(date '+%F %T')] $NAME: 完了（member の history を削除）"
