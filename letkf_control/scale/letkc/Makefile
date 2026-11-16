include ../configure

PROGS   = letkc efso

OBJS    = letkf_obs.o efso_tools.o letkf_tools.o obsope_tools_ctl.o

COMMON_DIR = ../common_letkc

COMMON_OBJS = $(COMMON_DIR)/SFMT.o           \
              $(COMMON_DIR)/common.o         \
              $(COMMON_DIR)/common_mpi.o     \
              $(COMMON_DIR)/$(common_mtx).o     \
              $(COMMON_DIR)/common_sort.o    \
              $(COMMON_DIR)/common_rand.o    \
              $(COMMON_DIR)/common_letkf.o   \
              $(COMMON_DIR)/common_ncio.o    \
              $(COMMON_DIR)/common_scale.o     \
              $(COMMON_DIR)/common_obs_scale.o \
              $(COMMON_DIR)/common_mpi_scale.o \
              $(COMMON_DIR)/common_nml.o

# convection（2026-11-07）: 観測演算子は LETKC 用のもの（obsope_tools_ctl.f90）を common_letkc でコンパイルする。
#   以前は ../common でコンパイルした ../obs/obsope_tools.o をリンクしていた（obs/ は LETKF・obsmake 用なので変えない）

INCS    = $(SCALE_INC) $(NETCDF_INC)

LIBS    = $(SCALE_LIB) $(NETCDF_LIB) $(LAPACK_LIB) $(KEVD_LIB)


.PHONY:	all clean FORCE

all:	$(PROGS)

letkc:	letkf.o $(COMMON_DIR)
	$(FC) $(FOPTS) $(FMCMODEL) -o letkc letkf.o \
	$(COMMON_OBJS) $(OBJS) $(SCALE_RM_OBJS) $(LIBS)

letkf.o:	letkf.f90 $(OBJS) $(COMMON_DIR)
	$(FC) $(FOPTS) -c $< -I$(COMMON_DIR) $(INCS)

letkf_obs.o:	letkf_obs.f90 $(COMMON_DIR)
	$(FC) $(FOPTS) -c $< -I$(COMMON_DIR) $(INCS)
letkf_tools.o:	letkf_tools.f90 letkf_obs.o efso_tools.o $(COMMON_DIR)
	$(FC) $(FOPTS) -c $< -I$(COMMON_DIR) $(INCS)

obsope_tools_ctl.o:	obsope_tools_ctl.f90 $(COMMON_DIR)
	$(FC) $(FOPTS) -c $< -I$(COMMON_DIR) $(INCS)

efso:	efso.o $(COMMON_DIR)
	$(FC) $(FOPTS) $(FMCMODEL) -o efso efso.o \
	$(COMMON_OBJS) $(OBJS) $(SCALE_RM_OBJS) $(LIBS)

efso.o:		efso.f90 $(OBJS) $(COMMON_DIR)
	$(FC) $(FOPTS) -c $< -I$(COMMON_DIR) $(INCS)

efso_tools.o:	efso_tools.f90 letkf_obs.o $(COMMON_DIR)
	$(FC) $(FOPTS) -c $< -I$(COMMON_DIR) $(INCS)

clean:
	rm -f *.o *.mod *.lst $(PROGS)

FORCE:
