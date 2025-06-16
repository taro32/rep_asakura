#!/bin/tcsh

ist=1
#ied=1
ied=100
totalmem=100
#totalmem=1
mem_ist=`printf "%03d" ${ist}`
mem_ied=`printf "%03d" ${ied}`

m=1
while [ ${m} -le ${totalmem} ]
do
 if [ ${m} -lt 10 ]; then
  member[${m}]="000${m}"
 elif [ ${m} -lt 100 ]; then
  member[${m}]="00${m}"
 elif [ ${m} -lt 1000 ]; then
  member[${m}]="0${m}"
 else
  member[${m}]="${m}"
 fi
 echo ${member[${m}]}
 cp -R ${m} letkfinput101/${member[${m}]}
 m=`expr ${m} + 1`
done

