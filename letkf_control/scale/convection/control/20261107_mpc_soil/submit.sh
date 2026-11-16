#!/bin/bash
#===============================================================================
# 土壌水分による降水の逐次の制御（MPC）を 1 本流す（2026-11-07。docs/control/notes.md 1.3）
#
# 使い方: control/20261107_mpc_soil/submit.sh <実験名> [KEY=値 ...]
#   例:   nohup control/20261107_mpc_soil/submit.sh r080 > /work/gv42/v42013/20260923_enkc_convection/mpc_soil/r080.log 2>&1 &
#         nohup control/20261107_mpc_soil/submit.sh nocontrol CONTROL=0 > …/nocontrol.log 2>&1 &   # 制御なし（比べる相手）
#   KEY（省略すると下の既定）:
#     CONTROL        1: 制御あり（既定）。0: 制御なし。目標値を −1.0 mm（絶対値）にし、この実験の &PARAM_CTLTARGET を
#                    「相対目標・相対誤差なし、負の差（y* − Ȳ < 0）を捨てる」にする。毎回 QC で捨てられて修正はかからないが、
#                    H(x)（各 member・mdet の Y）はログと obsdep に残る（case_tc の制御なし = 地上気圧 10 hPa と同じ考え方）
#     RATIO          y* = RATIO × Ȳ（既定 0.8）。controltarget の値の欄に書く。
#                    注意: RATIO=1.0 は制御なしにならない（mdet は y* − Y_mdet = Ȳ − Y_mdet で平均の側へ修正される）
#     SIGMAR_FACTOR  σ_R = SIGMAR_FACTOR × σ_Y（既定 1.0）。controltarget の誤差の欄に書く
#     TC             T_c [秒]（既定 3600）。Y の窓は t + TC ± 15 分。controltarget の dif（SLOT_BASE = t + 1 時間からの秒）を TC − 3600 に、
#                    予報の長さ CYCLEFLEN を TC + 900 にする（2026-11-08 に T_c = 3 時間の実験のため追加）
#     CTL_HOURS      介入する cycle の開始の時（START の日付の時、空白区切り。既定は空 = START〜LAST − 1 時間の毎時）。
#                    例: CTL_HOURS="14 15 16"。その時刻だけ $OUT/obs/controltarget_<t> を置き（SENS_CTL_TIMES=1。src/func_cycle_static.sh）、
#                    ほかの cycle は制御目標のファイルがない = 観測 0 個で、同化だけして制御はかけない（2026-11-09 追加）
#     LAMBDA         信号対雑音比の閾値（既定 0 = 使わない）。&PARAM_LETKC_CONTROL の CONTROL_LAMBDA
#     HORI_LOCAL     LETKC の水平の局所化 [m]（既定 1.0D6 = 領域全体）。LETKF（step 10）は変えない
#     LOG_LEVEL      LETKC のログの詳しさ（既定 1。2 で member ごとの H(x) も出す）
#     HIST_CLEAN     1: 各 cycle の LETKF の後に member の history・restart を消す（既定 1。試験の検算では 0）
#     KEEP_HIST_GUES 1: LETKC の前に step 3 の history を <時刻>/hist_gues/ に写す（既定 0。step 7 が hist/ を上書きするので、試験の検算用）
#     START          最初の cycle の開始 = 最初の介入の時刻（既定 20000131120000。result_m80 の解析から始める）
#     LAST           最後の解析時刻（既定 20000131180000。介入は START〜LAST − 1 時間に毎時）
#     TIME_LIMIT     ジョブの上限（既定 03:00:00）
#     MEMBER・RSCGRP  member 数（既定 80）・ジョブの rscgrp（既定 regular-o）
#   試験（配管の確認。2 member・1 cycle・debug-o 144 ノード）:
#         control/20261107_mpc_soil/submit.sh test_m2 MEMBER=2 RSCGRP=debug-o LAST=20000131130000 TIME_LIMIT=00:30:00 LOG_LEVEL=2 HIST_CLEAN=0 KEEP_HIST_GUES=1
#   T_c = 3 時間（2026-11-08。10〜17 時に介入）:
#         control/20261107_mpc_soil/submit.sh tc3_r080 TC=10800 START=20000131100000 TIME_LIMIT=04:00:00
#         control/20261107_mpc_soil/submit.sh tc3_nocontrol TC=10800 START=20000131100000 TIME_LIMIT=04:00:00 CONTROL=0
#   ピークの前後の 3 cycle だけ介入（2026-11-09。Y の窓の中心 t + T_c が 15・16・17 時。12 → 18 時を通す）:
#         control/20261107_mpc_soil/submit.sh p3_tc1 CTL_HOURS="14 15 16"
#         control/20261107_mpc_soil/submit.sh p3_tc3 TC=10800 CTL_HOURS="12 13 14" TIME_LIMIT=04:00:00
#         control/20261107_mpc_soil/submit.sh tc3_nocontrol TC=10800 TIME_LIMIT=04:00:00 CONTROL=0   # p3_tc3 と比べる相手
#
# 中身（docs/control/20261107_letkc_ctl_plan.md）:
#   - 毎 cycle（1 時間）: step 3 で t + 75 分まで予報 → step 4 で LETKC が controltarget（要素 19001。
#     make_obsin/controltarget/controltarget_mpc_areaprec の値・誤差を RATIO・SIGMAR_FACTOR に書き換えて $OUT/obs/controltarget に置く）を読み、
#     目標領域（中心 ±10 km、100 格子）の PREC の平均を t + 45〜75 分で積算した Y を観測演算子（letkc/obsope_tools_ctl.f90）で出し、
#     y* = RATIO × Ȳ、σ_R = SIGMAR_FACTOR × σ_Y で局所 ETKF → LAND_WATER の第 1・2 層だけを増やす向き・0〜0.5 で修正
#     （&PARAM_LETKC_CONTROL。member は ETKF の変換、mdet は自分の差とゲイン）→ step 7 で予報し直す → step 8 obsmake → step 10 LETKF
#   - LETKC の設定は config.nml.letkc の &PARAM_LETKC_CONTROL・HORI_LOCAL・LOG_LEVEL を置き換えた $OUT/config.nml.letkc（SENS_LETKC_NML。cycle_run.sh）
#   - 土壌水分のばらつきは足さない（摂動・inflation なし。土壌水分は同化の外。notes.md 1.3）
#   - history は全体 5 分ごと（スロットも 5 分）、PREC は 5 分の時間平均（SENS_PREC_TINTERVAL=300）
#   - member の history は各 cycle の LETKF の後に消す（HIST_CLEAN=1。既定）。Y・y*・σ_R は LETKC のログ（<時刻>/log/letkc/NOUT-*）と obsdep に残る
#   - 修正前は <時刻>/gues/（mdet・member）。修正量 = anal − gues
#
# 結果: /work/gv42/v42013/20260923_enkc_convection/mpc_soil/<実験名>/（使った設定は params.txt）
# 作業ディレクトリ: letkf_control/scale/tmp/convection_mpc_<実験名>
# cycle_run.sh はジョブが終わるまで待つので、nohup で流す
#===============================================================================
set -eu
cd "$(dirname "$0")/../.."                   # convection/

NAME=$1; shift
CONTROL=1; CTL_HOURS=; RATIO=0.8; SIGMAR_FACTOR=1.0; TC=3600; LAMBDA=0.0D0; HORI_LOCAL=1.0D6; LOG_LEVEL=1; HIST_CLEAN=1; KEEP_HIST_GUES=0
START=20000131120000; LAST=20000131180000; TIME_LIMIT=03:00:00; MEMBER=80; RSCGRP=regular-o
for kv in "$@"; do
  case ${kv%%=*} in
    CONTROL|CTL_HOURS|RATIO|SIGMAR_FACTOR|TC|LAMBDA|HORI_LOCAL|LOG_LEVEL|HIST_CLEAN|KEEP_HIST_GUES|START|LAST|TIME_LIMIT|MEMBER|RSCGRP) eval "${kv%%=*}=\"${kv#*=}\"" ;;
    *) echo "[Error] 知らない設定: $kv" >&2; exit 1 ;;
  esac
done

BASE=/work/gv42/v42013/20260923_enkc_convection
SRC=$BASE/result_m80                        # 制御なしの 24 時間の cycle（80 member + mdet）
OUT=$BASE/mpc_soil/$NAME
LCYCLE=3600
HALF_T=900                                  # Y の窓の半分 [秒]（config.nml.letkc の CTL_HALF_T(1)）
if (( TC < 900 || TC % 300 != 0 )); then echo "[Error] TC（$TC）は 900 以上・300 の倍数" >&2; exit 1; fi
grep -qE "CTL_HALF_T\(1\) *= *${HALF_T}(\.0)?D0" config.nml.letkc || { echo "[Error] config.nml.letkc の CTL_HALF_T(1) が $HALF_T でない" >&2; exit 1; }
CYCLEFLEN=$((TC + HALF_T))                  # t + TC + 15 分まで予報（Y の窓 t + TC ± 15 分。TC = 3600 で 4500）
CT_DIF=$((TC - LCYCLE))                     # controltarget の dif（SLOT_BASE = t + LCYCLE からの秒）
STIME=$START
CTL_TIMES=                                  # 介入する cycle の開始時刻（CTL_HOURS から）
if [ -n "$CTL_HOURS" ]; then
  [ "$CONTROL" = 1 ] || { echo "[Error] CTL_HOURS は CONTROL=1 のときだけ" >&2; exit 1; }
  for h in $CTL_HOURS; do
    t=${START:0:8}$(printf %02d $((10#$h)))0000
    if [[ ! $t > $(date -u -d "${START:0:8} ${START:8:2}:00 1 hour ago" +%Y%m%d%H%M%S) ]] || [[ ! $t < $LAST ]]; then
      echo "[Error] CTL_HOURS の $h 時が START〜LAST − 1 時間の外" >&2; exit 1
    fi
    CTL_TIMES="$CTL_TIMES $t"
  done
fi
ETIME=$(date -u -d "${LAST:0:8} ${LAST:8:2}:${LAST:10:2}:${LAST:12:2} $LCYCLE seconds ago" +%Y%m%d%H%M%S)   # 最後の cycle の開始時刻

if [ -e $OUT ]; then
  echo "[Error] $OUT がすでにあります。" >&2
  exit 1
fi
if [ ! -d $SRC/$STIME/anal/mdet ]; then
  echo "[Error] 初期値 $SRC/$STIME/anal がありません。" >&2
  exit 1
fi

# 初期値: result_m80 の START の解析（MEMBER 番までの member・mdet・mean・sprd）。LETKC・LETKF がその場で書き換えるのでコピーする
mkdir -p $OUT/$STIME $OUT/obs
mkdir -p $OUT/$STIME/anal
for mem in mdet mean sprd $(seq -f %04g $MEMBER); do   # MEMBER 番までの member（試験の 2 member なら 0001・0002）
  cp -r $SRC/$STIME/anal/$mem $OUT/$STIME/anal/
done

# 制御目標: controltarget_mpc_areaprec（要素 19001・種類 1・値 0.8・誤差 1.0）の値・誤差を RATIO・SIGMAR_FACTOR に書き換えて置く
if [ "$CONTROL" = 0 ]; then CT_VAL=-1.0; CT_ERR=1.0; else CT_VAL=$RATIO; CT_ERR=$SIGMAR_FACTOR; fi
python3 - make_obsin/controltarget/controltarget_mpc_areaprec $OUT/obs/controltarget $CT_VAL $CT_ERR $CT_DIF $CTL_TIMES <<'EOP'
import struct, sys
src, dst, ratio, fac, dif = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4]), float(sys.argv[5])
times = sys.argv[6:]   # CTL_HOURS のとき: 介入する時刻ごとに dst_<t> を置く（dst は置かない）
b = open(src, "rb").read()
assert len(b) == 40 and struct.unpack("<i", b[:4])[0] == 32, "controltarget の形式が違う"
wk = list(struct.unpack("<8f", b[4:36]))
assert int(wk[0]) == 19001, "要素番号が 19001 でない"
assert wk[7] == 0.0, "テンプレートの dif が 0 でない"
wk[4], wk[5], wk[7] = ratio, fac, dif
body = struct.pack("<8f", *wk)
for f in ([f"{dst}_{t}" for t in times] if times else [dst]):
    open(f, "wb").write(struct.pack("<i", 32) + body + struct.pack("<i", 32))
    print("controltarget:", f, wk)
EOP

# LETKC の設定: &PARAM_LETKC_CONTROL を土壌水分の制御に、HORI_LOCAL・LOG_LEVEL を引数の値に置き換える
python3 - config.nml.letkc $OUT/config.nml.letkc $LAMBDA $HORI_LOCAL $LOG_LEVEL $CONTROL <<'EOP'
import re, sys
src, dst, lam, hori, loglev, control = sys.argv[1:7]
s = open(src).read()
ctl = f"""&PARAM_LETKC_CONTROL
 CONTROL_VAR(1) = 'LAND_WATER_1', CONTROL_TARGET(1) = 'CTL', CONTROL_DIRECTION(1) = 'INCREASE',
 CONTROL_VMIN(1) = 0.0D0, CONTROL_VMAX(1) = 0.5D0, CONTROL_LAMBDA(1) = {lam},
 CONTROL_VAR(2) = 'LAND_WATER_2', CONTROL_TARGET(2) = 'CTL', CONTROL_DIRECTION(2) = 'INCREASE',
 CONTROL_VMIN(2) = 0.0D0, CONTROL_VMAX(2) = 0.5D0, CONTROL_LAMBDA(2) = {lam},
/"""
s, n1 = re.subn(r"^&PARAM_LETKC_CONTROL\n.*?^/", ctl, s, count=1, flags=re.M | re.S)
s, n2 = re.subn(r"^ *HORI_LOCAL *=.*$", f" HORI_LOCAL = {hori}, ! convection: control/20261107_mpc_soil/submit.sh", s, count=1, flags=re.M)
s, n3 = re.subn(r"^ *LOG_LEVEL *=.*$", f" LOG_LEVEL = {loglev},", s, count=1, flags=re.M)
assert (n1, n2, n3) == (1, 1, 1), (n1, n2, n3)
assert "&PARAM_CTLTARGET" in s
if control == "0":   # 制御なし: 種類 1 を「絶対値の目標・絶対値の誤差・負の差を捨てる」にする（目標値 −1.0 mm なので毎回捨てられる）
    for a, b in [("CTL_REL_TARGET(1) = .true.", "CTL_REL_TARGET(1) = .false."),
                 ("CTL_REL_ERROR(1) = .true.", "CTL_REL_ERROR(1) = .false."),
                 ("CTL_REJECT_NEGDEP(1) = .false.", "CTL_REJECT_NEGDEP(1) = .true.")]:
        assert s.count(a) == 1, a
        s = s.replace(a, b)
open(dst, "w").write(s)
EOP
echo "初期値: $SRC/$STIME/anal をコピー"

export SENS_OUTDIR=$OUT SENS_TMPSUBDIR=convection_mpc_$NAME
export SENS_OBS=$OUT/obs SENS_OBSMAKE_RUN=1     # 観測は修正後の mdet から毎 cycle 作る
export SENS_MEMBER=$MEMBER SENS_HIST_CLEAN=$HIST_CLEAN SENS_HIST_GUES_SAVE=$KEEP_HIST_GUES SENS_RSCGRP=$RSCGRP
[ -n "$CTL_TIMES" ] && export SENS_CTL_TIMES=1   # cycle ごとの controltarget_<t>（src/func_cycle_static.sh）
export SENS_CYCLEFLEN=$CYCLEFLEN SENS_PREC_TINTERVAL=300
# 案 A（2026-11-07。docs/control/20261107_letkc_ctl_plan.md）: history 全体を 5 分ごとにし、スロットも 5 分にする。
#   LETKC の観測演算子（letkc/obsope_tools_ctl.f90）は「スロット k = history の k 番目の時刻」で PREC の窓を積算する。
#   LETKC の SLOT_END は予報の終わり（CYCLEFLEN）まで広がる（src/func_cycle_static.sh）。LETKF の SLOT_END は t + LCYCLE のまま
export SENS_FCSTOUT=300 SENS_LTIMESLOT=300
export SENS_LETKC_NML=$OUT/config.nml.letkc

cat > $OUT/params.txt <<EOT
name=$NAME
CONTROL=$CONTROL
CTL_HOURS=$CTL_HOURS
CTL_TIMES=$CTL_TIMES
MEMBER=$MEMBER
RSCGRP=$RSCGRP
RATIO=$RATIO
SIGMAR_FACTOR=$SIGMAR_FACTOR
TC=$TC
CT_DIF=$CT_DIF
LAMBDA=$LAMBDA
HORI_LOCAL=$HORI_LOCAL
LOG_LEVEL=$LOG_LEVEL
HIST_CLEAN=$HIST_CLEAN
KEEP_HIST_GUES=$KEEP_HIST_GUES
controltarget=$OUT/obs/controltarget（CTL_HOURS のときは controltarget_<t>。make_obsin/controltarget/controltarget_mpc_areaprec の値・誤差・dif を RATIO・SIGMAR_FACTOR・TC − 3600 に）
letkc_nml=$OUT/config.nml.letkc
INIT=$SRC/$STIME/anal
STIME=$STIME
ETIME=$ETIME
LAST=$LAST
CYCLEFLEN=$CYCLEFLEN
PREC_TINTERVAL=300
FCSTOUT=300
LTIMESLOT=300
letkc=$(md5sum ../letkc/letkc | cut -c1-32)
submitted=$(date '+%Y-%m-%d %H:%M:%S')
EOT

echo "[$(date '+%F %T')] $NAME: cycle_run.sh を開始（$STIME〜$LAST）"
./cycle_run.sh $STIME $ETIME 1 10 static $TIME_LIMIT > $OUT/cycle_run.log 2>&1 || { echo "[Error] $NAME: cycle_run.sh が失敗（$OUT/cycle_run.log）" >&2; exit 1; }

# すべての cycle が正常に終わったか
jobid=$(grep -o "Job [0-9]* submitted" $OUT/cycle_run.log | awk '{print $2}')
jobout=../tmp/convection_mpc_$NAME/cycle_job.sh.$jobid.out
ncyc=$(( ( $(date -u -d "${LAST:0:8} ${LAST:8:2}:${LAST:10:2}" +%s) - $(date -u -d "${STIME:0:8} ${STIME:8:2}:${STIME:10:2}" +%s) ) / LCYCLE ))
nok=$(grep -c "SCALE-LETKF successfully completed" $jobout 2>/dev/null || true)
if [ "$nok" != "$ncyc" ]; then
  echo "[Error] $NAME: 正常に終わった cycle が $nok / $ncyc（$jobout）" >&2
  exit 1
fi
echo "[$(date '+%F %T')] $NAME: 完了（job $jobid）"
