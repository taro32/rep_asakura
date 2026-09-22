#!/bin/bash
#==============================================
#
# Generating initial conditions of ensemble idealized TC
# by Y.Saw 20240611
#
#=============================================

#ensemble size
MEMBER=101 

m=1
while [ "$m" -le "$MEMBER" ]; do
 mkdir -p $m
 cd $m
 cp ../init.conf_base init.conf
 conf_file_src=init.conf
 conf="$(cat $conf_file_src | \
           sed -e "/!--ENV_IN_SOUNDING_file--/a ENV_IN_SOUNDING_file = \"../ensperturb/env_perturb${m}.txt\"," \
          )"
 ((m++))
 echo "$conf" > $conf_file_src
 cp ../init.sh_base init.sh
 pjsub init.sh
 sleep 5
 cd ..
done
