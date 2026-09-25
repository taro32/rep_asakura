include ./configure

PROGS   = obsmakein_p

OBJS    = common_ncio.o

#OBJS_PAWR = radar_obs.o radar_tools.o dec_pawr_nml.o \
            read_toshiba$(TOSHIBA_OPT).o read_toshiba$(TOSHIBA_OPT)_f.o

#ifeq ($(USE_PAWR_DECODER),T)
#PROGS     += dec_pawr
#endif

COMMON_DIR = /work/gv42/v42013/scale-letkc/letkf_control/scale/common

COMMON_OBJS = $(COMMON_DIR)/SFMT.o           \
              $(COMMON_DIR)/common.o         \
              $(COMMON_DIR)/common_mpi.o     \
              $(COMMON_DIR)/common_scale.o     \
              $(COMMON_DIR)/common_obs_scale.o \
              $(COMMON_DIR)/common_mpi_scale.o \
              $(COMMON_DIR)/common_nml.o

INCS    = $(SCALE_INC) $(NETCDF_INC) -I$(SCALE_RM_OBJDIR)

LIBS    = $(SCALE_LIB) $(NETCDF_LIB) $(LAPACK_LIB)

.PHONY:	all clean FORCE

all:	$(PROGS)

obsmakein_p:	obsmakein_p.o $(OBJS) $(COMMON_DIR)
	$(FC) $(FOPTS) $(FMCMODEL) -o obsmakein_p obsmakein_p.o \
	$(COMMON_OBJS) $(OBJS) $(SCALE_RM_OBJS) $(LIBS)

obsmakein_p.o:	obsmakein_p.f90 $(OBJS) $(COMMON_DIR)
	$(FC) $(FOPTS) -c $< -I$(COMMON_DIR) $(INCS)


common_ncio.o:	common_ncio.f90  $(COMMON_DIR)
	$(FC) $(FOPTS) -c $< -I$(COMMON_DIR) $(INCS)

clean:
	rm -f *.o *.mod *.lst $(PROGS) obsope

FORCE:
