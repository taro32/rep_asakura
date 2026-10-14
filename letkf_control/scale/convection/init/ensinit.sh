#!/bin/bash
#===============================================================================
# 初期値（20 member + mdet）を作り直すための準備をする（Phase 7c、2026-10-03）
#
# rep_asakura の ensinit.sh と同じく、member ごとに
#   init.conf_base + ENV_IN_SOUNDING_file = ensperturb/env_perturb<m>.txt
# で scale-rm_init を実行する。違いは次のとおり。
#   - rep_asakura の 1/–101/ には書かない。作成先 GEN（下）に 1/–21/ を作る
#   - 静的入力（PARAG.29 など）は convection/dat/ の絶対パスにする
#   - 21 member を 1 本のジョブで順に作る（init_all.sh）。最後に md5 の記録 md5.txt を作る
#
# 使い方:
#   cd letkf_control/scale/convection/init
#   ./ensinit.sh [GEN]            # 準備だけ。最後に表示される pjsub を実行する
#
#   GEN の既定: /work/gv42/v42013/20260923_enkc_convection/init_20261003
#   作った初期値を OUTDIR に取り込むには（STIME の anal/ を空にしてから）:
#     SRC=<GEN> MD5_LIST=<GEN>/md5.txt ./import_rep_asakura.sh
#
# member の番号は rep_asakura と同じ（1–20 → 0001–0020、21 → mdet・mean）。
# 温位の乱数（RANDOM_THETA）の種は SCALE の既定（RANDOM_FIX = .false.）で、実行時刻とプロセス番号から決まる。
# そのため member ごとに独立だが、作り直すたびに変わる（同じ初期値は md5.txt と作ったファイルで残す）。
#===============================================================================
set -eu

cd "$(dirname "$0")"
INIT_DIR=$(pwd)
CONV_DIR=$(cd .. && pwd)
DAT=$CONV_DIR/dat
BIN=$(cd ../../../.. && pwd)/bin/scale-rm_init   # rep_asakura と同じ実行ファイル（case_tc/scale-rm_init はここへのリンク）

GEN=${1:-/work/gv42/v42013/20260923_enkc_convection/init_20261003}
NMEM=21
NPE=144
LABEL=init_20000101-000000.000

# 事前確認
[ -x "$BIN" ] || { echo "[Error] $BIN がありません。" >&2; exit 1; }
for m in $(seq 1 $NMEM); do
  [ -f ensperturb/env_perturb$m.txt ] || { echo "[Error] ensperturb/env_perturb$m.txt がありません。" >&2; exit 1; }
  if [ -n "$(ls -A $GEN/$m 2>/dev/null)" ]; then
    echo "[Error] $GEN/$m にすでにファイルがあります。上書きしないので止めます。" >&2
    exit 1
  fi
done
for f in param.bucket.conf PARAG.29 PARAPC.29 VARDATA.RM29 cira.nc MIPAS; do
  [ -e $DAT/$f ] || { echo "[Error] $DAT/$f がありません。" >&2; exit 1; }
done

# member ごとの init.conf と、使った摂動サウンディングの控え
for m in $(seq 1 $NMEM); do
  mkdir -p $GEN/$m
  cp ensperturb/env_perturb$m.txt $GEN/$m/
  sed -e "/!--ENV_IN_SOUNDING_file--/a ENV_IN_SOUNDING_file = \"$GEN/$m/env_perturb$m.txt\"," \
      -e "s#\"\.\./\(param\.bucket\.conf\|PARAG\.29\|PARAPC\.29\|VARDATA\.RM29\|cira\.nc\|MIPAS\)\"#\"$DAT/\1\"#" \
      init.conf_base > $GEN/$m/init.conf
  if grep -q '"\.\./' $GEN/$m/init.conf; then
    echo "[Error] $GEN/$m/init.conf に相対パス ../ が残っています。" >&2
    exit 1
  fi
done
cp ensperturb/sounding_perturb.py ensperturb/env.txt $GEN/

# ジョブスクリプト: init.sh_base の pjsub の設定と環境変数をそのまま使い、21 member を順に作る
{
  sed -n '1,/^export SCALE_NETCDF_INCLUDE/p' init.sh_base
  cat <<EOF
set -u
GEN=$GEN
for m in \$(seq 1 $NMEM); do
  cd \$GEN/\$m
  echo "[\$(date '+%F %T')] member \$m start"
  mpiexec $BIN ./init.conf
  n=\$(ls $LABEL.pe*.nc 2>/dev/null | wc -l)
  if [ "\$n" -ne $NPE ]; then
    echo "[Error] member \$m: 初期値のファイルが \$n 個です（$NPE 個必要）。" >&2
    exit 1
  fi
  echo "[\$(date '+%F %T')] member \$m done"
done
cd \$GEN
md5sum */$LABEL.pe*.nc > md5.txt
chmod a-w */$LABEL.pe*.nc
echo "[\$(date '+%F %T')] all done: md5.txt"
EOF
} > $GEN/init_all.sh
chmod u+x $GEN/init_all.sh

echo "準備しました: $GEN/{1..$NMEM}/init.conf, $GEN/init_all.sh"
echo "ジョブの投入:"
echo "  cd $GEN && pjsub init_all.sh"
