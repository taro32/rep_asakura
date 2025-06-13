#!/bin/sh
#--------------pjsub option-------------------
#PJM -L "rscgrp=regular-o"
#PJM -L "node=16"
#PJM --mpi "proc=64"
#PJM --omp "thread=12"
#PJM -L "elapse=10:00:00"
#PJM -g "jh250035o"
#PJM -j
#--------------------------------------------
export SCALE_SYS="FX700"
export SCALE_NETCDF_LIBS="-L/work/opt/local/aarch64/apps/fj/1.2.31/hdf5/1.12.0/lib -L/work/opt/local/aarch64/apps/fj/1.2.31/netcdf/4.7.4/lib  -lnetcdf -lnetcdff -lhdf5_hl -lhdf5_fortran -lhdf5 -lm -lz"
LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/work/opt/local/aarch64/apps/fj/1.2.31/hdf5/1.12.0/lib:/work/opt/local/aarch64/apps/fj/1.2.31/netcdf/4.7.4/lib:/work/opt/local/aarch64/apps/fj/1.2.31/netcdf-fortran/4.5.3/lib 
export LD_LIBRARY_PATH
export SCALE_NETCDF_INCLUDE="-I//work/opt/local/aarch64/apps/fj/1.2.31/netcdf/4.7.4/include"
mpiexec ./scale-rm run.conf
