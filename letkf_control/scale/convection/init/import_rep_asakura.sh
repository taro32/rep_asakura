#!/bin/bash
#===============================================================================
# rep_asakura で作成済みの初期値を $OUTDIR/$STIME/anal/ にコピーする（Phase 4）
#
# 使い方:
#   cd letkf_control/scale/convection/init
#   ./import_rep_asakura.sh [OUTDIR]
#
#   OUTDIR を省略すると ../config.main から読む。
#
# member の対応（ここだけで定義する）:
#   rep_asakura 1/ – 20/  →  anal/0001/ – anal/0020/
#   rep_asakura 21/       →  anal/mdet/
#   rep_asakura 21/       →  anal/mean/  （case_tc と同じく mdet のコピー。
#                                          step 3 で mean も予報するため置き場所として必要）
#
# - コピー先にすでにファイルがあれば、上書きせずに止まる。
# - コピー元は読み取り専用なので、コピー後に書き込み権限を付ける
#   （LETKC・LETKF が restart をその場で上書きするため）。
# - コピー後、docs/phase0/init_1-21.md5 と照合する。
#===============================================================================
set -eu

cd "$(dirname "$0")"
INIT_DIR=$(pwd)

SRC=/work/02/gv42/v42013/scale-letkc/scale-rm/test/case/rep_asakura
MD5_LIST=$INIT_DIR/../docs/phase0/init_1-21.md5
STIME=20000101000000                      # コピー元のファイル名の時刻に合わせて固定
LABEL=init_20000101-000000.000            # コピー元・コピー先のファイル名
NMEM=20
NPE=144

if [ $# -ge 1 ]; then
  OUTDIR=$1
elif [ -f ../config.main ]; then
  OUTDIR=$(cd .. && . ./config.main && echo "$OUTDIR")
else
  echo "[Error] OUTDIR を引数で指定するか、../config.main を用意してください。" >&2
  exit 1
fi
if [ -f ../config.cycle ]; then
  STIME_CFG=$(cd .. && . ./config.cycle && echo "$STIME")
  if [ "$STIME_CFG" != "$STIME" ]; then
    echo "[Error] config.cycle の STIME ($STIME_CFG) がコピー元の時刻 ($STIME) と違います。" >&2
    exit 1
  fi
fi

DEST=$OUTDIR/$STIME/anal
echo "コピー元: $SRC"
echo "コピー先: $DEST"

# コピー元 → コピー先 の対応
declare -a SRC_MEM DEST_MEM
for m in $(seq 1 $NMEM); do
  SRC_MEM+=("$m");  DEST_MEM+=("$(printf %04d $m)")
done
SRC_MEM+=(21 21);   DEST_MEM+=(mdet mean)

# 事前確認: コピー元がそろっていること、コピー先が空であること
for i in "${!SRC_MEM[@]}"; do
  s=$SRC/${SRC_MEM[$i]}
  n=$(ls $s/$LABEL.pe*.nc 2>/dev/null | wc -l)
  if [ "$n" -ne $NPE ]; then
    echo "[Error] $s のファイルが $n 個です（$NPE 個必要）。" >&2
    exit 1
  fi
  d=$DEST/${DEST_MEM[$i]}
  if [ -n "$(ls -A $d 2>/dev/null)" ]; then
    echo "[Error] $d にすでにファイルがあります。上書きしないので止めます。" >&2
    exit 1
  fi
done

# コピー
for i in "${!SRC_MEM[@]}"; do
  s=$SRC/${SRC_MEM[$i]}
  d=$DEST/${DEST_MEM[$i]}
  mkdir -p $d
  cp $s/$LABEL.pe*.nc $d/
  chmod u+w $d/$LABEL.pe*.nc
  echo "  ${SRC_MEM[$i]}/ -> ${DEST_MEM[$i]}/"
done

# 照合: Phase 0 で記録した md5 と比べる
echo "md5 を照合しています..."
nerr=0
for i in "${!SRC_MEM[@]}"; do
  sm=${SRC_MEM[$i]}
  dm=${DEST_MEM[$i]}
  # 記録の "  <md5>  <sm>/<file>" を、コピー先のパスに置き換えて md5sum -c に渡す
  if ! grep " ${sm}/$LABEL\." $MD5_LIST | sed "s| ${sm}/| $DEST/$dm/|" | md5sum -c --quiet; then
    nerr=$((nerr + 1))
    echo "[Error] $dm の md5 が記録と一致しません。" >&2
  fi
done
if [ $nerr -ne 0 ]; then
  exit 1
fi
echo "完了: ${#SRC_MEM[@]} member × $NPE ファイル、すべて md5 が一致しました。"
