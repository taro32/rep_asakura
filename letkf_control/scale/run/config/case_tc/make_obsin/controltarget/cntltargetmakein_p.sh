#!/bin/bash 
#
#PJM -g "jh220020o" 
#PJM -L "rscgrp=debug-o"
#PJM -L "node=1"
#PJM -L "elapse=00:30:00"
#PJM -j
#PJM -X
#
#
export SCALE_SYS="FX700"
export SCALE_NETCDF_LIBS="-L/work/opt/local/aarch64/apps/fj/1.2.31/hdf5/1.12.0/lib -L/work/opt/local/aarch64/apps/fj/1.2.31/netcdf/4.7.4/lib  -lnetcdf -lnetcdff -lhdf5_hl -lhdf5_fortran -lhdf5 -lm -lz"
LD_LIBRARY_PATH=/opt/FJSVxtclanga/tcsds-1.2.39/lib64:/work/opt/local/aarch64/apps/fj/1.2.31/hdf5/1.12.0/lib:/work/opt/local/aarch64/apps/fj/1.2.31/netcdf/4.7.4/lib:/work/opt/local/aarch64/apps/fj/1.2.31/netcdf-fortran/4.5.3/lib
export LD_LIBRARY_PATH
export SCALE_NETCDF_INCLUDE="-I//work/opt/local/aarch64/apps/fj/1.2.31/netcdf/4.7.4/include"

./cntltargetmakein_p

