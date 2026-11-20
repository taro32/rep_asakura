#!/bin/bash
#===============================================================================
# 土壌水分による降水の逐次の制御（MPC）を 1 本流す。LETKC の修正を論文の形（同じ増分を mdet と全 member に足す）に直した版
# （2026-11-16。docs/control/notes.md 3.11。もとは control/20261107_mpc_soil/submit.sh。違いは下の「20261107 版との違い」）
#
# 使い方: control/20261116_mpc_same/submit.sh <実験名> [KEY=値 ...]
#   例（ピークの前後の 3 cycle、T_c = 3 時間。3.10 の p3_tc3 の流し直し）:
#     mkdir -p /work/gv42/v42013/20260923_enkc_convection/mpc_same
#     nohup control/20261116_mpc_same/submit.sh p3_tc3 TC=10800 CTL_HOURS="12 13 14" TIME_LIMIT=03:30:00 NNODES=1116 \
#       > /work/gv42/v42013/20260923_enkc_convection/mpc_same/p3_tc3.log 2>&1 &
#   KEY（省略すると下の既定）:
#     CONTROL        1: 制御あり（既定）。0: 制御なし（目標値 −1.0 mm の絶対値・負の差を捨てる → 毎回 QC で捨てられる）
#     RATIO          y* = RATIO × Ȳ（既定 0.8）。controltarget の値の欄に書く
#     SIGMAR_FACTOR  σ_R = SIGMAR_FACTOR × σ_Y（既定 1.0）。controltarget の誤差の欄に書く
#     TC             T_c [秒]（既定 3600）。Y の窓は t + TC ± 15 分。予報の長さは TC + 900
#     CTL_HOURS      介入する cycle の開始の時（空白区切り。既定は空 = 毎時）。その時刻だけ $OUT/obs/controltarget_<t> を置く
#     LAMBDA         信号対雑音比の閾値（既定 0 = 使わない）。&PARAM_LETKC_CONTROL の CONTROL_LAMBDA
#     HORI_LOCAL     LETKC の水平の局所化 [m]（既定 1.0D6 = 領域全体）
#     LOG_LEVEL      LETKC のログの詳しさ（既定 1）
#     HIST_CLEAN     1: 各 cycle の LETKF の後に member の history・restart を消す（既定 1）
#     KEEP_HIST_GUES 1: step 3 の history を <時刻>/hist_gues/ に写す（既定 0）
#     START・LAST    最初の cycle の開始・最後の解析時刻（既定 20000131120000・20000131180000）
#     TIME_LIMIT     ジョブの上限（既定 03:00:00）
#     MEMBER・RSCGRP  member 数（既定 80）・rscgrp（既定 regular-o）
#     NNODES         ジョブのノード数（既定は空 = config の値。1116 で large-o に入る。p3_tc3 は約 2 時間 50 分）
#
# 20261107 版との違い:
#   - LETKC の修正: 増分 Δx = Xᵇ w̄（member 平均の移動、w̄ ∝ y* − Ȳ）を 1 本作り、mdet と全 member に同じく足す
#     （&PARAM_LETKC_CONTROL の CONTROL_LEGACY_TRANSMD = .false. を $OUT/config.nml.letkc に明示する。letkc/letkf_tools.f90）。
#     20261107 版は mdet を自分の差 y* − H(x_mdet)（transmd）で修正していた
#   - 結果の置き場所: /work/gv42/v42013/20260923_enkc_convection/mpc_same/<実験名>/（20261107 版は mpc_soil/）
#   - 作業ディレクトリ: letkf_control/scale/tmp/convection_mpcsame_<実験名>
#   - NNODES を引数で渡せる（20261107 版は SENS_NNODES を外で export していた）
#
# そのほか（制御目標・観測演算子・制約・history の出力・観測の作り方）は 20261107 版と同じ:
#   毎 cycle: step 3 で予報 → step 4 LETKC（目標領域 ±10 km の PREC を t + TC ± 15 分で積算した Y、y* = RATIO × Ȳ、
#   LAND_WATER の第 1・2 層を増やす向き・0〜0.5）→ step 7 予報し直し → step 8 obsmake（修正後の mdet から）→ step 10 LETKF
# 結果: <置き場所>/<実験名>/（使った設定は params.txt）。修正前は <時刻>/gues/、修正量 = anal − gues
# cycle_run.sh はジョブが終わるまで待つので、nohup で流す
#===============================================================================
set -eu
cd "$(dirname "$0")/../.."                   # convection/

NAME=$1; shift
CONTROL=1; CTL_HOURS=; RATIO=0.8; SIGMAR_FACTOR=1.0; TC=3600; LAMBDA=0.0D0; HORI_LOCAL=1.0D6; LOG_LEVEL=1; HIST_CLEAN=1; KEEP_HIST_GUES=0; NNODES=
START=20000131120000; LAST=20000131180000; TIME_LIMIT=03:00:00; MEMBER=80; RSCGRP=regular-o
for kv in "$@"; do
  case ${kv%%=*} in
    CONTROL|CTL_HOURS|RATIO|SIGMAR_FACTOR|TC|LAMBDA|HORI_LOCAL|LOG_LEVEL|HIST_CLEAN|KEEP_HIST_GUES|START|LAST|TIME_LIMIT|MEMBER|RSCGRP|NNODES) eval "${kv%%=*}=\"${kv#*=}\"" ;;
    *) echo "[Error] 知らない設定: $kv" >&2; exit 1 ;;
  esac
done

BASE=/work/gv42/v42013/20260923_enkc_convection
SRC=$BASE/result_m80                        # 制御なしの 24 時間の cycle（80 member + mdet）
OUT=$BASE/mpc_same/$NAME
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
 CONTROL_LEGACY_TRANSMD = .false.,
/"""
s, n1 = re.subn(r"^&PARAM_LETKC_CONTROL\n.*?^/", ctl, s, count=1, flags=re.M | re.S)
s, n2 = re.subn(r"^ *HORI_LOCAL *=.*$", f" HORI_LOCAL = {hori}, ! convection: control/20261116_mpc_same/submit.sh", s, count=1, flags=re.M)
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

export SENS_OUTDIR=$OUT SENS_TMPSUBDIR=convection_mpcsame_$NAME
export SENS_OBS=$OUT/obs SENS_OBSMAKE_RUN=1     # 観測は修正後の mdet から毎 cycle 作る
export SENS_MEMBER=$MEMBER SENS_HIST_CLEAN=$HIST_CLEAN SENS_HIST_GUES_SAVE=$KEEP_HIST_GUES SENS_RSCGRP=$RSCGRP
[ -n "$CTL_TIMES" ] && export SENS_CTL_TIMES=1   # cycle ごとの controltarget_<t>（src/func_cycle_static.sh）
export SENS_CYCLEFLEN=$CYCLEFLEN SENS_PREC_TINTERVAL=300
# 案 A（2026-11-07。docs/control/20261107_letkc_ctl_plan.md）: history 全体を 5 分ごとにし、スロットも 5 分にする。
#   LETKC の観測演算子（letkc/obsope_tools_ctl.f90）は「スロット k = history の k 番目の時刻」で PREC の窓を積算する。
#   LETKC の SLOT_END は予報の終わり（CYCLEFLEN）まで広がる（src/func_cycle_static.sh）。LETKF の SLOT_END は t + LCYCLE のまま
export SENS_FCSTOUT=300 SENS_LTIMESLOT=300
export SENS_LETKC_NML=$OUT/config.nml.letkc
[ -n "$NNODES" ] && export SENS_NNODES=$NNODES

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
NNODES=$NNODES
CONTROL_LEGACY_TRANSMD=.false.
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
jobout=../tmp/convection_mpcsame_$NAME/cycle_job.sh.$jobid.out
ncyc=$(( ( $(date -u -d "${LAST:0:8} ${LAST:8:2}:${LAST:10:2}" +%s) - $(date -u -d "${STIME:0:8} ${STIME:8:2}:${STIME:10:2}" +%s) ) / LCYCLE ))
nok=$(grep -c "SCALE-LETKF successfully completed" $jobout 2>/dev/null || true)
if [ "$nok" != "$ncyc" ]; then
  echo "[Error] $NAME: 正常に終わった cycle が $nok / $ncyc（$jobout）" >&2
  exit 1
fi
echo "[$(date '+%F %T')] $NAME: 完了（job $jobid）"
