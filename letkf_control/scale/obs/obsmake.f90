PROGRAM obsmake
!=======================================================================
!
! [PURPOSE:] Main program of synthetic observation generator
!
! [HISTORY:]
!   November 2014  Guo-Yuan Lien     Created
!   .............  See git history for the following revisions
!
!=======================================================================
!$USE OMP_LIB
  USE common
  USE common_mpi
  USE common_scale
  USE common_mpi_scale
  USE common_obs_scale
  USE common_nml
  USE obsope_tools
  IMPLICIT NONE

  character(len=7) :: stdoutf = '-000000'
  character(len=6400) :: icmd
  integer tmp1, tmp2, ierr

!-----------------------------------------------------------------------
! Initial settings
!-----------------------------------------------------------------------

  call initialize_mpi_scale 
  call mpi_timer('', 1)

  if (command_argument_count() >= 2) then
    call get_command_argument(2, icmd)
    if (trim(icmd) /= '') then
      write (stdoutf(2:7), '(I6.6)') myrank
!      write (6,'(3A,I6.6)') 'STDOUT goes to ', trim(icmd)//stdoutf, ' for MYRANK ', myrank
      open (6, file=trim(icmd)//stdoutf)
      write (6,'(A,I6.6,2A)') 'MYRANK=', myrank, ', STDOUTF=', trim(icmd)//stdoutf
    end if
  end if

!-----------------------------------------------------------------------

  call set_mem_node_proc(1)
  !call set_mem_node_proc(MEMBER+2) ! YSaw 20250625
  
  !if (myrank > 63) then
  !  myrank_use = .false.
  !endif
  call set_scalelib('OBSMAKE')
  !write(6,*) "starting ... ", myrank, myrank_use
  call set_common_scale
  call set_common_mpi_scale
  call set_common_obs_scale
  !write(6,*) "my status ... ", myrank_d, myrank_use, MPI_COMM_a, MPI_COMM_d, MPI_COMM_u, MPI_COMM_WORLD

  if (myrank_use) then

    !call set_common_scale
    !call set_common_mpi_scale
    !call set_common_obs_scale
    
    call mpi_timer('INITIALIZE', 1, barrier=universal_comm)
   

 
!-----------------------------------------------------------------------
! Read observations
!-----------------------------------------------------------------------

    allocate(obs(OBS_IN_NUM))
    call read_obs_all(obs)

    call mpi_timer('READ_OBS', 1, barrier=universal_comm)
    !call mpi_timer('READ_OBS', 1, barrier=MPI_COMM_a) !YSaw 20250624
    !call mpi_timer('READ_OBS', 1, barrier=MPI_COMM_e)


!-----------------------------------------------------------------------
! Generate observations
!-----------------------------------------------------------------------
    !if (myrank < 64) then ! YSaw debugging
    call obsmake_cal(obs)
    !endif

    call mpi_timer('OBSMAKE', 1, barrier=universal_comm)
    !call mpi_timer('OBSMAKE', 1, barrier=MPI_COMM_a) !YSaw 20250624
    !call mpi_timer('OBSMAKE', 1, barrier=MPI_COMM_e)
    deallocate(obs)

    !call unset_common_mpi_scale

  end if ! [ myrank_use ]

  !write(6,*) "ending ....", myrank
!  call unset_common_mpi_scale
!  call unset_scalelib

!-----------------------------------------------------------------------
! Finalize
!-----------------------------------------------------------------------

 

  call MPI_BARRIER(universal_comm, ierr)
  !call unset_common_mpi_scale
  !call unset_scalelib
  call mpi_timer('FINALIZE', 1, barrier=universal_comm)
  !write(6,*) "really finalizing...", myrank
  !call MPI_Finalize(ierr)
  call finalize_mpi_scale

  STOP
END PROGRAM obsmake
