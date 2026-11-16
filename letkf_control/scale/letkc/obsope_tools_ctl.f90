MODULE obsope_tools_ctl
!=======================================================================
!
! [PURPOSE:] Observation operator for LETKC (control targets)
!
!   convection（2026-11-07）: obs/obsope_tools.f90 の obsope_cal を写し、LETKC 用に分けたもの。
!   obs/（LETKF・obsmake）は変えない。common_letkc でコンパイルする。
!
!   足したもの: 制御目標の要素（is_ctl_obs。今は id_ctl_areaacc）の分岐。
!     id_ctl_areaacc: 2 次元の history の変数 CTL_VAR(typ) を、中心（controltarget の経度・緯度）から
!       x・y に CTL_HALF_X(typ)・CTL_HALF_Y(typ) 以内の格子で平均し（CTL_AREA_OP = 'MEAN'）、
!       時間の窓 (dif − CTL_HALF_T, dif + CTL_HALF_T] に時刻が入るスロットで
!       積算（CTL_TIME_OP = 'SUM': 値 × SLOT_TINTERVAL）または平均（'MEAN'）する。
!       dif は、ほかの観測と同じく SLOT_BASE の時刻からの秒。
!       スロット k の時刻は (k − SLOT_BASE) × SLOT_TINTERVAL。時間平均（TAVERAGE）の history は
!       区間の終わりの時刻で書かれるので、(dif − HALF_T, dif + HALF_T] の区間をちょうど覆う。
!       そのため、その変数の history の間隔は SLOT_TINTERVAL と同じであること（案 A: 全体 5 分）。
!
!   観測 1 つは、ふつうの観測と同じく「中心の subdomain・dif のスロット」に割り当てる（バケツソートはそのまま）。
!   値は、各プロセスが自分の subdomain・各スロットについて領域内の格子の部分和を出し、
!   member ごとに MPI_COMM_d で足し合わせて、その観測を受け持つプロセスの obsda に値と QC を入れる。
!   そのあと（set_letkf_obs の QC・局所 ETKF・obsdep などの診断）はふつうの観測と同じ道を通る。
!
!   目標の種類を増やすとき: is_ctl_obs（common_obs_scale.f90）に要素を足し、
!   ctl_setup の select case（領域の決め方）と ctl_finish の select case（値の決め方）に分岐を足す。
!
! [HISTORY:]
!   November 2014  Guo-Yuan Lien  created (obs/obsope_tools.f90)
!   .............  See git history for the following revisions
!
!=======================================================================
!$USE OMP_LIB
  USE common
  USE common_mpi
  USE common_scale
  USE common_mpi_scale
  USE common_obs_scale
  use common_nml
!  use scale_prc, only: &
!    PRC_myrank
!    MPI_COMM_d => LOCAL_COMM_WORLD
  use scale_atmos_grid_cartesC_index, only: &
    KHALO, IHALO, JHALO, IS, IE, JS, JE
  use scale_atmos_grid_cartesC, only: &
    DX, DY

  IMPLICIT NONE
  PRIVATE
  PUBLIC :: obsope_cal

  ! convection: 制御目標（is_ctl_obs の要素）の情報。全プロセスが同じものを持つ（obs(:) は全プロセスにある）
  integer, save :: nctl = 0                      ! 制御目標の数（OBSDA_RUN のファイルにあり、領域の中にあるもの）
  integer, allocatable, save :: ctl_set(:)       ! obs の set
  integer, allocatable, save :: ctl_idx(:)       ! obs の idx
  integer, allocatable, save :: ctl_nn(:)        ! 自分の obsda の中の位置（受け持たないなら 0）
  integer, allocatable, save :: ctl_iv2d(:)      ! v2dg の変数の番号
  logical, allocatable, save :: ctl_ok(:)        ! 値を計算するか（.false. なら qc を ctl_qc に）
  integer, allocatable, save :: ctl_qc(:)        ! ctl_ok = .false. のときの qc
  real(r_size), allocatable, save :: ctl_wt(:,:) ! (slot, k) スロットの重み（窓の外は 0）
  logical, allocatable, save :: ctl_mask(:,:,:)  ! (i, j, k) 自分の subdomain の格子が領域に入るか（i = IS..IE, j = JS..JE）
  real(r_size), allocatable, save :: ctl_ncell(:) ! 領域の格子の数（全 subdomain の合計）

CONTAINS

!-----------------------------------------------------------------------
! Observation operator calculation
!-----------------------------------------------------------------------
SUBROUTINE obsope_cal(obsda_return, nobs_extern)
  IMPLICIT NONE

  type(obs_da_value), optional, intent(out) :: obsda_return
  integer, optional, intent(in) :: nobs_extern

  type(obs_da_value) :: obsda

  integer :: it, im, iof, islot, ierr
  integer :: n, nn, nsub, nmod, n1, n2

  integer :: nobs     ! observation number processed in this subroutine
  integer :: nobs_all
  integer :: nobs_max_per_file
  integer :: nobs_max_per_file_sub
  integer :: slot_nobsg

  integer :: ip, ibufs
  integer, allocatable :: cntr(:), dspr(:)
  integer, allocatable :: cnts(:), dsps(:)
  integer, allocatable :: bsn(:,:), bsna(:,:), bsnext(:,:)
  integer :: islot_time_out, islot_domain_out

  integer, allocatable :: obrank_bufs(:)
  real(r_size), allocatable :: ri_bufs(:)
  real(r_size), allocatable :: rj_bufs(:)

  integer, allocatable :: obset_bufs(:)
  integer, allocatable :: obidx_bufs(:)

  integer :: slot_id(SLOT_START:SLOT_END)
  real(r_size) :: slot_lb(SLOT_START:SLOT_END)
  real(r_size) :: slot_ub(SLOT_START:SLOT_END)

  real(r_size), allocatable :: v3dg(:,:,:,:)
  real(r_size), allocatable :: v2dg(:,:,:)

  real(r_size), allocatable :: mv3dg(:,:,:,:,:)
  real(r_size), allocatable :: mv2dg(:,:,:,:)

  real(r_size), allocatable :: mdbz3dg(:,:,:,:)
  real(r_size), allocatable :: slope3dg(:,:,:)

  real(r_size) :: ril, rjl, rk, rkz

  character(filelenmax) :: obsdafile
  character(len=11) :: obsda_suffix = '.000000.dat'
  character(len=4) :: nstr
  character(len=timer_name_width) :: timer_str

  real(r_size), allocatable :: ctl_psum(:)   ! convection: 制御目標の部分和（この member・この subdomain）
  integer, allocatable :: ctl_nmiss(:)       ! convection: 欠損値の数

!-------------------------------------------------------------------------------

  call mpi_timer('', 2)

!-------------------------------------------------------------------------------
! First scan of all observation data: Compute their horizontal location and time
!-------------------------------------------------------------------------------

  nobs_all = 0
  nobs_max_per_file = 0
  do iof = 1, OBS_IN_NUM
    if (obs(iof)%nobs > nobs_max_per_file) then
      nobs_max_per_file = obs(iof)%nobs
    end if
    if (OBSDA_RUN(iof)) then
      nobs_all = nobs_all + obs(iof)%nobs
    end if
  end do

!  obs_set_TCX = -1
!  obs_set_TCY = -1
!  obs_set_TCP = -1
!  obs_idx_TCX = -1
!  obs_idx_TCY = -1
!  obs_idx_TCP = -1

  nobs_max_per_file_sub = (nobs_max_per_file - 1) / nprocs_a + 1
  allocate (obrank_bufs(nobs_max_per_file_sub))
  allocate (ri_bufs(nobs_max_per_file_sub))
  allocate (rj_bufs(nobs_max_per_file_sub))

  allocate (cntr(nprocs_a))
  allocate (dspr(nprocs_a))

  ! Use all processes to compute the basic obsevration information
  ! (locations in model grids and the subdomains they belong to)
  !-----------------------------------------------------------------------------

  do iof = 1, OBS_IN_NUM
    if (obs(iof)%nobs > 0) then ! Process basic obsevration information for all observations since this information is not saved in obsda files
                                ! when using separate observation operators; ignore the 'OBSDA_RUN' setting for this section
      nsub = obs(iof)%nobs / nprocs_a
      nmod = mod(obs(iof)%nobs, nprocs_a)
      do ip = 1, nmod
        cntr(ip) = nsub + 1
      end do
      do ip = nmod+1, nprocs_a
        cntr(ip) = nsub
      end do
      dspr(1) = 0
      do ip = 2, nprocs_a
        dspr(ip) = dspr(ip-1) + cntr(ip-1)
      end do

      obrank_bufs(:) = -1
!$OMP PARALLEL DO PRIVATE(ibufs,n) SCHEDULE(STATIC)
      do ibufs = 1, cntr(myrank_a+1)
        n = dspr(myrank_a+1) + ibufs
!        select case (obs(iof)%elm(n))
!        case (id_tclon_obs)
!          obs_set_TCX = iof
!          obs_idx_TCX = n
!          cycle
!        case (id_tclat_obs)
!          obs_set_TCY = iof
!          obs_idx_TCY = n
!          cycle
!        case (id_tcmip_obs)
!          obs_set_TCP = iof
!          obs_idx_TCP = n
!          cycle
!        end select

        call phys2ij(obs(iof)%lon(n), obs(iof)%lat(n), ri_bufs(ibufs), rj_bufs(ibufs))
        call rij_rank(ri_bufs(ibufs), rj_bufs(ibufs), obrank_bufs(ibufs))
      end do ! [ ibufs = 1, cntr(myrank_a+1) ]
!$OMP END PARALLEL DO

      call mpi_timer('obsope_cal:first_scan_cal:', 2, barrier=MPI_COMM_a)

      call MPI_ALLGATHERV(obrank_bufs, cntr(myrank_a+1), MPI_INTEGER, obs(iof)%rank, cntr, dspr, MPI_INTEGER, MPI_COMM_a, ierr)
      call MPI_ALLGATHERV(ri_bufs,     cntr(myrank_a+1), MPI_r_size,  obs(iof)%ri,   cntr, dspr, MPI_r_size,  MPI_COMM_a, ierr)
      call MPI_ALLGATHERV(rj_bufs,     cntr(myrank_a+1), MPI_r_size,  obs(iof)%rj,   cntr, dspr, MPI_r_size,  MPI_COMM_a, ierr)

      call mpi_timer('obsope_cal:first_scan_reduce:', 2)
    end if ! [ obs(iof)%nobs > 0 ]
  end do ! [ do iof = 1, OBS_IN_NUM ]

  deallocate (cntr, dspr)
  deallocate (obrank_bufs, ri_bufs, rj_bufs)

  ! Bucket sort of observation wrt. time slots and subdomains using the process rank 0
  !-----------------------------------------------------------------------------

  islot_time_out = SLOT_END + 1   ! slot = SLOT_END+1 for observation not in the assimilation time window
  islot_domain_out = SLOT_END + 2 ! slot = SLOT_END+2 for observation outside of the model domain

  allocate (bsn   (SLOT_START  :SLOT_END+2, 0:nprocs_d-1))
  allocate (bsna  (SLOT_START-1:SLOT_END+2, 0:nprocs_d-1))

  if (myrank_e == 0) then
    allocate ( obset_bufs(nobs_all) )
    allocate ( obidx_bufs(nobs_all) )
  end if

  if (myrank_a == 0) then
    allocate (bsnext(SLOT_START  :SLOT_END+2, 0:nprocs_d-1))
    bsn(:,:) = 0
    bsna(:,:) = 0
    bsnext(:,:) = 0

!$OMP PARALLEL PRIVATE(iof,n,islot)
    do iof = 1, OBS_IN_NUM
      if (OBSDA_RUN(iof) .and. obs(iof)%nobs > 0) then
!$OMP DO SCHEDULE(STATIC)
        do n = 1, obs(iof)%nobs
          if (obs(iof)%rank(n) == -1) then
            ! process the observations outside of the model domain in process rank 0
!$OMP ATOMIC
            bsn(islot_domain_out, 0) = bsn(islot_domain_out, 0) + 1
          else
            islot = ceiling(obs(iof)%dif(n) / SLOT_TINTERVAL - 0.5d0) + SLOT_BASE
            if (islot < SLOT_START .or. islot > SLOT_END) then
              islot = islot_time_out
            end if
!$OMP ATOMIC
            bsn(islot, obs(iof)%rank(n)) = bsn(islot, obs(iof)%rank(n)) + 1
          end if
        end do ! [ n = 1, obs(iof)%nobs ]
!$OMP END DO
      end if ! [ OBSDA_RUN(iof) .and. obs(iof)%nobs > 0 ]
    end do ! [ do iof = 1, OBS_IN_NUM ]
!$OMP END PARALLEL

    do ip = 0, nprocs_d-1
      if (ip > 0) then
        bsna(SLOT_START-1, ip) = bsna(SLOT_END+2, ip-1)
      end if
      do islot = SLOT_START, SLOT_END+2
        bsna(islot, ip) = bsna(islot-1, ip) + bsn(islot, ip)
      end do
      bsnext(SLOT_START:SLOT_END+2, ip) = bsna(SLOT_START-1:SLOT_END+1, ip)
    end do

    do iof = 1, OBS_IN_NUM
      if (OBSDA_RUN(iof) .and. obs(iof)%nobs > 0) then
        do n = 1, obs(iof)%nobs
          if (obs(iof)%rank(n) == -1) then
            ! process the observations outside of the model domain in process rank 0
            bsnext(islot_domain_out, 0) = bsnext(islot_domain_out, 0) + 1
            obset_bufs(bsnext(islot_domain_out, 0)) = iof
            obidx_bufs(bsnext(islot_domain_out, 0)) = n
          else
            islot = ceiling(obs(iof)%dif(n) / SLOT_TINTERVAL - 0.5d0) + SLOT_BASE
            if (islot < SLOT_START .or. islot > SLOT_END) then
              islot = islot_time_out
            end if
            bsnext(islot, obs(iof)%rank(n)) = bsnext(islot, obs(iof)%rank(n)) + 1
            obset_bufs(bsnext(islot, obs(iof)%rank(n))) = iof
            obidx_bufs(bsnext(islot, obs(iof)%rank(n))) = n
          end if
        end do ! [ n = 1, obs(iof)%nobs ]
      end if ! [ OBSDA_RUN(iof) .and. obs(iof)%nobs > 0 ]
    end do ! [ do iof = 1, OBS_IN_NUM ]

    deallocate (bsnext)

    call mpi_timer('obsope_cal:bucket_sort:', 2)
  end if ! [ myrank_a == 0 ]

  ! Broadcast the bucket-sort observation numbers to all processes and print
  !-----------------------------------------------------------------------------

  call mpi_timer('', 2, barrier=MPI_COMM_a)

  call MPI_BCAST(bsn,  (SLOT_END-SLOT_START+3)*nprocs_d, MPI_INTEGER, 0, MPI_COMM_a, ierr)
  call MPI_BCAST(bsna, (SLOT_END-SLOT_START+4)*nprocs_d, MPI_INTEGER, 0, MPI_COMM_a, ierr)

  call mpi_timer('obsope_cal:sort_info_bcast:', 2)

  do islot = SLOT_START, SLOT_END
    slot_id(islot) = islot - SLOT_START + 1
    slot_lb(islot) = (real(islot - SLOT_BASE, r_size) - 0.5d0) * SLOT_TINTERVAL
    slot_ub(islot) = (real(islot - SLOT_BASE, r_size) + 0.5d0) * SLOT_TINTERVAL
  end do

  if (LOG_LEVEL >= 2) then
    write (nstr, '(I4)') SLOT_END - SLOT_START + 1
    write (6, *)
    write (6, '(A,I6,A)') 'OBSERVATION COUNTS BEFORE QC (FROM OBSOPE):'
    write (6, '(A,'//nstr//"('=========='),A)") '====================', '===================='
    write (6, '(A,'//nstr//'I10.4)') '            SLOT #  ', slot_id(:)
    write (6, '(A,'//nstr//'F10.1)') '            FROM (s)', slot_lb(:)
    write (6, '(A,'//nstr//'F10.1,A)') 'SUBDOMAIN #   TO (s)', slot_ub(:), '  OUT_TIME     TOTAL'
    write (6, '(A,'//nstr//"('----------'),A)") '--------------------', '--------------------'
    do ip = 0, nprocs_d-1
      write (6, '(I11.6,9x,'//nstr//'I10,2I10)') ip, bsn(SLOT_START:SLOT_END, ip), bsn(islot_time_out, ip), bsna(SLOT_END+1, ip) - bsna(SLOT_START-1, ip)
    end do
    write (6, '(A,'//nstr//"('----------'),A)") '--------------------', '--------------------'
    write (6, '(A,'//nstr//'(10x),10x,I10)') ' OUT_DOMAIN         ', bsn(islot_domain_out, 0)
    write (6, '(A,'//nstr//"('----------'),A)") '--------------------', '--------------------'
    write (6, '(A,'//nstr//'I10,2I10)') '      TOTAL         ', sum(bsn(SLOT_START:SLOT_END, :), dim=2), sum(bsn(islot_time_out, :)), bsna(SLOT_END+2, nprocs_d-1)
    write (6, '(A,'//nstr//"('=========='),A)") '====================', '===================='
  end if

  ! Scatter the basic obsevration information to processes group {myrank_e = 0},
  ! each of which only gets the data in its own subdomain
  !-----------------------------------------------------------------------------

  nobs = bsna(SLOT_END+2, myrank_d) - bsna(SLOT_START-1, myrank_d)

  obsda%nobs = nobs
  call obs_da_value_allocate(obsda, 0)

  if (present(obsda_return)) then
    if (present(nobs_extern)) then
      obsda_return%nobs = nobs + nobs_extern
    else
      obsda_return%nobs = nobs
    end if
    call obs_da_value_allocate(obsda_return, nitmax)
  end if

  if (myrank_e == 0) then
    allocate (cnts(nprocs_d))
    allocate (dsps(nprocs_d))
    do ip = 0, nprocs_d-1
      dsps(ip+1) = bsna(SLOT_START-1, ip)
      cnts(ip+1) = bsna(SLOT_END+2, ip) - dsps(ip+1)
    end do

    call MPI_SCATTERV(obset_bufs, cnts, dsps, MPI_INTEGER, obsda%set, cnts(myrank_d+1), MPI_INTEGER, 0, MPI_COMM_d, ierr)
    call MPI_SCATTERV(obidx_bufs, cnts, dsps, MPI_INTEGER, obsda%idx, cnts(myrank_d+1), MPI_INTEGER, 0, MPI_COMM_d, ierr)

    call mpi_timer('obsope_cal:mpi_scatterv:', 2)

    deallocate (cnts, dsps)
    deallocate (obset_bufs, obidx_bufs)
  end if ! [ myrank_e == 0 ]

  ! Broadcast the basic obsevration information
  ! from processes group {myrank_e = 0} to all processes
  !-----------------------------------------------------------------------------

  call mpi_timer('', 2, barrier=MPI_COMM_e)

  call MPI_BCAST(obsda%set, nobs, MPI_INTEGER, 0, MPI_COMM_e, ierr)
  call MPI_BCAST(obsda%idx, nobs, MPI_INTEGER, 0, MPI_COMM_e, ierr)

  if (present(obsda_return)) then
    obsda_return%set(1:nobs) = obsda%set
    obsda_return%idx(1:nobs) = obsda%idx
  end if

  call mpi_timer('obsope_cal:mpi_broadcast:', 2)

  ! convection: 制御目標（領域・時間の窓で積算する要素）の準備
  !-----------------------------------------------------------------------------
  call ctl_setup(obsda, nobs)
  allocate (ctl_psum(max(nctl,1)))
  allocate (ctl_nmiss(max(nctl,1)))

  call mpi_timer('obsope_cal:ctl_setup:', 2)

!-------------------------------------------------------------------------------
! Second scan of observation data in own subdomain: Compute H(x), QC, ... etc.
!-------------------------------------------------------------------------------

  allocate ( v3dg (nlevh,nlonh,nlath,nv3dd) )
  allocate ( v2dg (nlonh,nlath,nv2dd) )

  if ( RADAR_ADDITIVE_Y18 ) then
    allocate ( mv3dg (SLOT_END-SLOT_START+1,nlevh,nlonh,nlath,nv3dd) )
    allocate ( mv2dg (SLOT_END-SLOT_START+1,nlonh,nlath,nv2dd) )
    allocate ( mdbz3dg(SLOT_END-SLOT_START+1,nlev,nlon,nlat) )

    allocate ( slope3dg (SLOT_END-SLOT_START+1,nlevh,nv3dd) )

    call get_history_ensemble_mean_mpi( mv3dg, mv2dg, mdbz3dg )
    call mpi_timer('obsope_cal:get_mean_Y18:', 2)
    call get_regression_slope_dbz_mpi( mv3dg, mv2dg, mdbz3dg, slope3dg )
    call mpi_timer('obsope_cal:get_slope_Y18:', 2)
  endif

  do it = 1, nitmax
    im = myrank_to_mem(it)
    if ((im >= 1 .and. im <= MEMBER) .or. im == mmdetin) then

      if ( LOG_OUT ) write (6,'(A,I6.6,A,I4.4,A,I6.6)') 'MYRANK ',myrank,' is processing member ', &
                                                        im, ', subdomain id #', myrank_d

      if (nobs > 0) then
        obsda%qc(1:nobs) = iqc_undef
      end if

      ! Observations not in the assimilation time window
      ! 
      n1 = bsna(islot_time_out-1, myrank_d) - bsna(SLOT_START-1, myrank_d) + 1
      n2 = bsna(islot_time_out,   myrank_d) - bsna(SLOT_START-1, myrank_d)
      if (n1 <= n2) then
        obsda%qc(n1:n2) = iqc_time
      end if

      ! Observations outside of the model domain
      ! 
      n1 = bsna(islot_domain_out-1, myrank_d) - bsna(SLOT_START-1, myrank_d) + 1
      n2 = bsna(islot_domain_out,   myrank_d) - bsna(SLOT_START-1, myrank_d)
      if (n1 <= n2) then
        obsda%qc(n1:n2) = iqc_out_h
      end if

      ! convection: 制御目標の部分和を 0 に
      ctl_psum(:) = 0.0d0
      ctl_nmiss(:) = 0

      ! Valid observations: loop over time slots
      ! 
      do islot = SLOT_START, SLOT_END
        if ( LOG_OUT )write (6, '(A,I3,A,F9.1,A,F9.1,A)') 'Slot #', islot-SLOT_START+1, ': time window (', slot_lb(islot), ',', slot_ub(islot), '] sec'

        n1 = bsna(islot-1, myrank_d) - bsna(SLOT_START-1, myrank_d) + 1
        n2 = bsna(islot,   myrank_d) - bsna(SLOT_START-1, myrank_d)
        slot_nobsg = sum(bsn(islot, :))

        if (slot_nobsg <= 0 .and. .not. ctl_need_slot(islot)) then ! convection: 制御目標の窓に入るスロットは読む
          write (6, '(A)') ' -- no observations found in this time slot... do not need to read model data'
          cycle
        end if

        if ( LOG_OUT ) then
          write (6, '(A,I10)') ' -- # obs in the slot = ', slot_nobsg
          write (6, '(A,I6,A,I6,A,I10)') ' -- # obs in the slot and processed by rank ', myrank, ' (subdomain #', myrank_d, ') = ', bsn(islot, myrank_d)
        end if

        call mpi_timer('', 2)

        call read_ens_history_iter(it, islot, v3dg, v2dg)

        write (timer_str, '(A30,I4,A7,I4,A2)') 'obsope_cal:read_ens_history(t=', it, ', slot=', islot, '):'
        call mpi_timer(trim(timer_str), 2)

        ! convection: 制御目標の部分和（自分の subdomain・このスロット）
        call ctl_accum(islot, v2dg, ctl_psum, ctl_nmiss)

!$omp parallel do private(nn,n,iof,ril,rjl,rk,rkz)
        do nn = n1, n2
          iof = obsda%set(nn)
          n = obsda%idx(nn)

          if (is_ctl_obs(obs(iof)%elm(n))) cycle ! convection: 制御目標はスロットの後でまとめて（ctl_finish）

          call rij_g2l(myrank_d, obs(iof)%ri(n), obs(iof)%rj(n), ril, rjl)

          if (.not. USE_OBS(obs(iof)%typ(n))) then
            obsda%qc(nn) = iqc_otype
            cycle
          end if

          select case (OBS_IN_FORMAT(iof))
          !=====================================================================
          case (obsfmt_prepbufr)
          !---------------------------------------------------------------------
            call phys2ijk(v3dg(:,:,:,iv3dd_p), obs(iof)%elm(n), ril, rjl, obs(iof)%lev(n), rk, obsda%qc(nn), typ=obs(iof)%typ(n))
            if (obsda%qc(nn) == iqc_good) then
              call Trans_XtoY(obs(iof)%elm(n), ril, rjl, rk, &
                              obs(iof)%lon(n), obs(iof)%lat(n), v3dg, v2dg, obsda%val(nn), obsda%qc(nn), typ=obs(iof)%typ(n))
            end if
          !=====================================================================
          case (obsfmt_radar, obsfmt_radar_nc)
          !---------------------------------------------------------------------
            if (obs(iof)%lev(n) > RADAR_ZMAX) then
              obsda%qc(nn) = iqc_radar_vhi
              if (LOG_LEVEL >= 3) then
                write(6,'(A,F8.1,A,I5)') '[Warning] radar observation is too high: lev=', obs(iof)%lev(n), ', elem=', obs(iof)%elm(n)
              end if
            elseif (obs(iof)%lev(n) < RADAR_ZMIN) then
              obsda%qc(nn) = iqc_out_vlo
              if (LOG_LEVEL >= 3) then
                write(6,'(A,F8.1,A,I5)') '[Warning] radar observation is too low: lev=', obs(iof)%lev(n), ', elem=', obs(iof)%elm(n)
              end if
            else
              call phys2ijkz(v3dg(:,:,:,iv3dd_hgt), ril, rjl, obs(iof)%lev(n), rkz, obsda%qc(nn))
            end if
            if (obsda%qc(nn) == iqc_good) then
              if ( RADAR_ADDITIVE_Y18 ) then
                call Trans_XtoY_radar(obs(iof)%elm(n), obs(iof)%meta(1), obs(iof)%meta(2), obs(iof)%meta(3), ril, rjl, rkz,       &
                                      obs(iof)%lon(n), obs(iof)%lat(n), obs(iof)%lev(n), v3dg, v2dg, obsda%val(nn), obsda%qc(nn), &
                                      mv3d=mv3dg(islot-SLOT_START+1,:,:,:,:), slope3d=slope3dg(islot-SLOT_START+1,:,:), &
                                      ref_add=obsda%pert(nn) )
              else
                call Trans_XtoY_radar(obs(iof)%elm(n), obs(iof)%meta(1), obs(iof)%meta(2), obs(iof)%meta(3), ril, rjl, rkz, &
                                      obs(iof)%lon(n), obs(iof)%lat(n), obs(iof)%lev(n), v3dg, v2dg, obsda%val(nn), obsda%qc(nn))
              endif
              if (obsda%qc(nn) == iqc_ref_low) obsda%qc(nn) = iqc_good ! when process the observation operator, we don't care if reflectivity is too small

              if (RADAR_PQV) then
                call itpl_3d( v3dg(:,:,:,iv3dd_p), rkz, ril, rjl, obsda%pm(nn) )
                call itpl_3d( v3dg(:,:,:,iv3dd_t), rkz, ril, rjl, obsda%tm(nn) )
                call itpl_3d( v3dg(:,:,:,iv3dd_q), rkz, ril, rjl, obsda%qv(nn) )
              end if

              !!!!!! may not need to do this at this stage !!!!!!
              !if (obs(iof)%elm(n) == id_radar_ref_obs) then
              !  obsda%val(nn) = 10.0d0 * log10(obsda%val(nn))
              !end if
              !!!!!!
            end if
          end select


        end do ! [ nn = n1, n2 ]
!$omp end parallel do
 
        write (timer_str, '(A30,I4,A7,I4,A2)') 'obsope_cal:obsope_step_2   (t=', it, ', slot=', islot, '):'
        call mpi_timer(trim(timer_str), 2)
      end do ! [ islot = SLOT_START, SLOT_END ]

      ! convection: 制御目標の部分和を MPI_COMM_d で足し、受け持つプロセスの obsda に値と QC を入れる
      call ctl_finish(obsda, nobs, im, ctl_psum, ctl_nmiss)

      call mpi_timer('', 2)

      ! Write obsda data to files if OBSDA_OUT = .true.
      ! 
      if (OBSDA_OUT) then
!        write (6,'(A,I6.6,A,I4.4,A,I6.6)') 'MYRANK ',myrank,' is writing observations for member ', &
!              im, ', subdomain id #', myrank_d
        if (im <= MEMBER) then
          obsdafile = OBSDA_OUT_BASENAME
          call filename_replace_mem(obsdafile, im)
        else if (im == mmean) then
          obsdafile = OBSDA_MEAN_OUT_BASENAME
        else if (im == mmdet) then
          obsdafile = OBSDA_MDET_OUT_BASENAME
        end if
        write (obsda_suffix(2:7),'(I6.6)') myrank_d
        write (6,'(A,I6.6,2A)') 'MYRANK ', myrank,' is writing an obsda file ', trim(obsdafile)//obsda_suffix
        call write_obs_da(trim(obsdafile)//obsda_suffix,obsda,0)

        write (timer_str, '(A30,I4,A2)') 'obsope_cal:write_obs_da    (t=', it, '):'
        call mpi_timer(trim(timer_str), 2)
      end if

      ! Prepare variables that will need to be communicated if obsda_return is given
      ! 
      if (present(obsda_return)) then
        if ( RADAR_PQV ) then
          call obs_da_value_partial_reduce_iter(obsda_return, it, 1, nobs, obsda%val, obsda%qc, qv=obsda%qv, tm=obsda%tm, pm=obsda%pm )
        elseif ( RADAR_ADDITIVE_Y18 ) then
          call obs_da_value_partial_reduce_iter(obsda_return, it, 1, nobs, obsda%val, obsda%qc, pert=obsda%pert)
        else
          call obs_da_value_partial_reduce_iter(obsda_return, it, 1, nobs, obsda%val, obsda%qc )
        endif

        write (timer_str, '(A30,I4,A2)') 'obsope_cal:partial_reduce  (t=', it, '):'
        call mpi_timer(trim(timer_str), 2)
      end if ! [ present(obsda_return) ]

    end if ! [ (im >= 1 .and. im <= MEMBER) .or. im == mmdetin ]
  end do ! [ it = 1, nitmax ]

  if ( RADAR_ADDITIVE_Y18 ) then
    deallocate ( mv3dg, mv2dg, mdbz3dg )
    deallocate ( slope3dg )
  endif

  deallocate ( v3dg, v2dg )
  deallocate ( bsn, bsna )
  deallocate ( ctl_psum, ctl_nmiss )
  call ctl_free
  call obs_da_value_deallocate(obsda)

  return
end subroutine obsope_cal

!-----------------------------------------------------------------------
! convection: 制御目標の準備（obsope_cal の第 1 の走査の後に呼ぶ。全プロセスで呼ぶ）
!   全プロセスが obs(:) を持つので、目標の一覧・窓・領域は各プロセスが自分で決める（通信は格子の数の合計だけ）。
!-----------------------------------------------------------------------
subroutine ctl_setup(obsda, nobs)
  implicit none
  type(obs_da_value), intent(in) :: obsda
  integer, intent(in) :: nobs

  integer :: iof, n, k, nn, islot, ityp, iv, i, j, ig, jg, nwin, nin, ierr
  real(r_size) :: tau, t0, t1, ri, rj
  real(r_size), parameter :: eps_t = 1.0d-3   ! [s]
  real(r_size), parameter :: eps_x = 1.0d-3   ! [m]

  call ctl_free

  ! 1. 一覧
  nctl = 0
  do iof = 1, OBS_IN_NUM
    if (OBSDA_RUN(iof) .and. obs(iof)%nobs > 0) then
      do n = 1, obs(iof)%nobs
        if (is_ctl_obs(obs(iof)%elm(n)) .and. obs(iof)%rank(n) /= -1) nctl = nctl + 1
      end do
    end if
  end do
  if (nctl == 0) return

  allocate (ctl_set(nctl), ctl_idx(nctl), ctl_nn(nctl), ctl_iv2d(nctl), ctl_ok(nctl), ctl_qc(nctl))
  allocate (ctl_wt(SLOT_START:SLOT_END, nctl))
  allocate (ctl_mask(IS:IE, JS:JE, nctl))
  allocate (ctl_ncell(nctl))
  ctl_nn(:) = 0
  ctl_iv2d(:) = 0
  ctl_ok(:) = .true.
  ctl_qc(:) = iqc_good
  ctl_wt(:,:) = 0.0d0
  ctl_mask(:,:,:) = .false.
  ctl_ncell(:) = 0.0d0

  k = 0
  do iof = 1, OBS_IN_NUM
    if (OBSDA_RUN(iof) .and. obs(iof)%nobs > 0) then
      do n = 1, obs(iof)%nobs
        if (is_ctl_obs(obs(iof)%elm(n)) .and. obs(iof)%rank(n) /= -1) then
          k = k + 1
          ctl_set(k) = iof
          ctl_idx(k) = n
        end if
      end do
    end if
  end do

  ! 2. 自分の obsda の中の位置（バケツソートで、中心の subdomain のプロセスに割り当てられている）
  do nn = 1, nobs
    iof = obsda%set(nn)
    n = obsda%idx(nn)
    if (.not. is_ctl_obs(obs(iof)%elm(n))) cycle
    do k = 1, nctl
      if (ctl_set(k) == iof .and. ctl_idx(k) == n) then
        ctl_nn(k) = nn
        exit
      end if
    end do
  end do

  do k = 1, nctl
    iof = ctl_set(k)
    n = ctl_idx(k)
    ityp = obs(iof)%typ(n)

    ! 3. 種類（&PARAM_CTLTARGET の行）
    if (ityp < 1 .or. ityp > nobtype) then
      ctl_ok(k) = .false.
      ctl_qc(k) = iqc_otype
      if (myrank_a == 0) write (6, '(A,I8,A,I6)') '[Warning] CTLTARGET: typ out of range: obs #', n, ', typ = ', ityp
      cycle
    end if
    if (.not. USE_OBS(ityp)) then
      ctl_ok(k) = .false.
      ctl_qc(k) = iqc_otype
      cycle
    end if
    if (len_trim(CTL_VAR(ityp)) == 0) then
      ctl_ok(k) = .false.
      ctl_qc(k) = iqc_otype
      if (myrank_a == 0) write (6, '(A,I3)') '[Warning] CTLTARGET: CTL_VAR is not set in &PARAM_CTLTARGET for typ ', ityp
      cycle
    end if

    select case (obs(iof)%elm(n))
    !===================================================================
    case (id_ctl_areaacc)
    !-------------------------------------------------------------------
      ! 変数（history の 2 次元の変数のうち read_history が読むもの）
      do iv = 1, nv2dd_use
        if (trim(v2dd_name(iv)) == trim(CTL_VAR(ityp)) .and. v2dd_hastime(iv)) then
          ctl_iv2d(k) = iv
          exit
        end if
      end do
      if (ctl_iv2d(k) == 0) then
        write (6, '(3A)') "[Error] CTLTARGET: CTL_VAR = '", trim(CTL_VAR(ityp)), &
                          "' is not a time-dependent 2D history variable read by LETKC (v2dd_name in common_scale.f90)"
        stop 99
      end if

      ! 時間の窓: (dif − HALF_T, dif + HALF_T] に時刻が入るスロット。HALF_T = 0 は dif のスロット 1 つ
      if (CTL_HALF_T(ityp) > 0.0d0) then
        nwin = nint(2.0d0 * CTL_HALF_T(ityp) / SLOT_TINTERVAL)
        if (abs(real(nwin, r_size) * SLOT_TINTERVAL - 2.0d0 * CTL_HALF_T(ityp)) > eps_t) then
          write (6, '(A,I3,2F12.2)') '[Error] CTLTARGET: 2 * CTL_HALF_T is not a multiple of SLOT_TINTERVAL: typ, HALF_T, SLOT_TINTERVAL = ', &
                                      ityp, CTL_HALF_T(ityp), SLOT_TINTERVAL
          stop 99
        end if
        t0 = obs(iof)%dif(n) - CTL_HALF_T(ityp)
        t1 = obs(iof)%dif(n) + CTL_HALF_T(ityp)
        nin = 0
        do islot = SLOT_START, SLOT_END
          tau = real(islot - SLOT_BASE, r_size) * SLOT_TINTERVAL
          if (tau > t0 + eps_t .and. tau <= t1 + eps_t) then
            nin = nin + 1
            ctl_wt(islot, k) = 1.0d0
          end if
        end do
      else
        nwin = 1
        nin = 0
        islot = ceiling(obs(iof)%dif(n) / SLOT_TINTERVAL - 0.5d0) + SLOT_BASE
        if (islot >= SLOT_START .and. islot <= SLOT_END) then
          nin = 1
          ctl_wt(islot, k) = 1.0d0
        end if
      end if
      if (nin /= nwin) then                ! 窓が SLOT_START〜SLOT_END をはみ出す
        ctl_ok(k) = .false.
        ctl_qc(k) = iqc_time
        ctl_wt(:, k) = 0.0d0
        if (myrank_a == 0) write (6, '(A,I8,A,2I4)') '[Warning] CTLTARGET: time window is not covered by the slots: obs #', n, &
                                                    ', slots in window / needed = ', nin, nwin
        cycle
      end if
      select case (trim(CTL_TIME_OP(ityp)))
      case ('SUM')
        ctl_wt(:, k) = ctl_wt(:, k) * SLOT_TINTERVAL   ! 時間平均の値 × 間隔 = 積算
      case ('MEAN')
        ctl_wt(:, k) = ctl_wt(:, k) / real(nwin, r_size)
      end select

      ! 領域: 中心から |x| <= HALF_X、|y| <= HALF_Y の格子（格子の中心で判定）
      ri = obs(iof)%ri(n)
      rj = obs(iof)%rj(n)
      do j = JS, JE
        do i = IS, IE
          call ij_l2g(myrank_d, i, j, ig, jg)
          if (abs(real(ig, r_size) - ri) * DX <= CTL_HALF_X(ityp) + eps_x .and. &
              abs(real(jg, r_size) - rj) * DY <= CTL_HALF_Y(ityp) + eps_x) then
            ctl_mask(i, j, k) = .true.
          end if
        end do
      end do
      ctl_ncell(k) = real(count(ctl_mask(:, :, k)), r_size)
    !===================================================================
    case default
    !-------------------------------------------------------------------
      write (6, '(A,I6)') '[Error] CTLTARGET: unsupported control target element: ', obs(iof)%elm(n)
      stop 99
    end select
  end do ! [ k = 1, nctl ]

  ! 領域の格子の数（全 subdomain。どの member の組でも同じ）
  call MPI_ALLREDUCE(MPI_IN_PLACE, ctl_ncell, nctl, MPI_r_size, MPI_SUM, MPI_COMM_d, ierr)

  do k = 1, nctl
    if (ctl_ok(k) .and. ctl_ncell(k) < 0.5d0) then
      ctl_ok(k) = .false.
      ctl_qc(k) = iqc_out_h
      ctl_wt(:, k) = 0.0d0
      if (myrank_a == 0) write (6, '(A,I8)') '[Warning] CTLTARGET: no grid point in the target area: obs #', ctl_idx(k)
    end if
  end do

  if (myrank_a == 0 .and. LOG_LEVEL >= 1) then
    write (6, '(A,I6)') 'CTLTARGET: number of control targets = ', nctl
    do k = 1, nctl
      iof = ctl_set(k)
      n = ctl_idx(k)
      write (6, '(A,I4,A,I6,A,I3,A,F10.1,A,L2,A,F8.0,A,I4,A,I4)') 'CTLTARGET #', k, ': elm =', obs(iof)%elm(n), &
            ', typ =', obs(iof)%typ(n), ', dif =', obs(iof)%dif(n), ', ok =', ctl_ok(k), ', ncell =', ctl_ncell(k), &
            ', slots =', count(ctl_wt(:, k) /= 0.0d0), ', subdomain =', obs(iof)%rank(n)
    end do
  end if

  return
end subroutine ctl_setup

!-----------------------------------------------------------------------
! convection: このスロットの history を読む必要があるか（制御目標の窓に入るか）
!-----------------------------------------------------------------------
logical function ctl_need_slot(islot)
  implicit none
  integer, intent(in) :: islot

  ctl_need_slot = .false.
  if (nctl == 0) return
  ctl_need_slot = any(ctl_wt(islot, :) /= 0.0d0)
end function ctl_need_slot

!-----------------------------------------------------------------------
! convection: このスロットの部分和（自分の subdomain の領域内の格子の和 × スロットの重み）
!-----------------------------------------------------------------------
subroutine ctl_accum(islot, v2dg, psum, nmiss)
  implicit none
  integer, intent(in) :: islot
  real(r_size), intent(in) :: v2dg(nlonh,nlath,nv2dd)
  real(r_size), intent(inout) :: psum(:)
  integer, intent(inout) :: nmiss(:)
  integer :: k, i, j
  real(r_size) :: s
  real(r_size), parameter :: vmiss = -1.0d29   ! これより小さい値は欠損（SCALE の RMISS・UNDEF は −9.9999e30）

  do k = 1, nctl
    if (.not. ctl_ok(k)) cycle
    if (ctl_wt(islot, k) == 0.0d0) cycle
    s = 0.0d0
    do j = JS, JE
      do i = IS, IE
        if (ctl_mask(i, j, k)) then
          if (v2dg(i, j, ctl_iv2d(k)) < vmiss) then
            nmiss(k) = nmiss(k) + 1
          else
            s = s + v2dg(i, j, ctl_iv2d(k))
          end if
        end if
      end do
    end do
    psum(k) = psum(k) + ctl_wt(islot, k) * s
  end do

  return
end subroutine ctl_accum

!-----------------------------------------------------------------------
! convection: 部分和を MPI_COMM_d で足し、受け持つプロセスの obsda に値と QC を入れる
!   MPI_COMM_d の全プロセス（同じ member の組）が同じ it で呼ぶ
!-----------------------------------------------------------------------
subroutine ctl_finish(obsda, nobs, im, psum, nmiss)
  implicit none
  type(obs_da_value), intent(inout) :: obsda
  integer, intent(in) :: nobs
  integer, intent(in) :: im
  real(r_size), intent(inout) :: psum(:)
  integer, intent(inout) :: nmiss(:)
  integer :: k, nn, iof, n, ityp, ierr

  if (nctl == 0) return

  call MPI_ALLREDUCE(MPI_IN_PLACE, psum,  nctl, MPI_r_size,  MPI_SUM, MPI_COMM_d, ierr)
  call MPI_ALLREDUCE(MPI_IN_PLACE, nmiss, nctl, MPI_INTEGER, MPI_SUM, MPI_COMM_d, ierr)

  do k = 1, nctl
    nn = ctl_nn(k)
    if (nn <= 0 .or. nn > nobs) cycle          ! 受け持たない
    if (obsda%qc(nn) /= iqc_undef) cycle       ! 窓の外（iqc_time）・領域の外（iqc_out_h）はバケツソートで決まっている
    iof = ctl_set(k)
    n = ctl_idx(k)

    if (.not. ctl_ok(k)) then
      obsda%qc(nn) = ctl_qc(k)
      obsda%val(nn) = undef
      cycle
    end if
    if (nmiss(k) > 0) then
      obsda%qc(nn) = iqc_obs_bad
      obsda%val(nn) = undef
      write (6, '(A,I4,A,I6,A,I8)') '[Warning] CTLTARGET #', k, ': missing values in history, member ', im, ', count = ', nmiss(k)
      cycle
    end if

    ityp = obs(iof)%typ(n)
    select case (obs(iof)%elm(n))
    case (id_ctl_areaacc)
      select case (trim(CTL_AREA_OP(ityp)))
      case ('MEAN')
        obsda%val(nn) = psum(k) / ctl_ncell(k)
      end select
    end select
    obsda%qc(nn) = iqc_good

    if (LOG_LEVEL >= 2) then
      write (6, '(A,I4,A,I6,A,ES14.6)') 'CTLTARGET #', k, ': member ', im, ', H(x) = ', obsda%val(nn)
    end if
  end do

  return
end subroutine ctl_finish

!-----------------------------------------------------------------------
subroutine ctl_free
  implicit none
  if (allocated(ctl_set))   deallocate (ctl_set)
  if (allocated(ctl_idx))   deallocate (ctl_idx)
  if (allocated(ctl_nn))    deallocate (ctl_nn)
  if (allocated(ctl_iv2d))  deallocate (ctl_iv2d)
  if (allocated(ctl_ok))    deallocate (ctl_ok)
  if (allocated(ctl_qc))    deallocate (ctl_qc)
  if (allocated(ctl_wt))    deallocate (ctl_wt)
  if (allocated(ctl_mask))  deallocate (ctl_mask)
  if (allocated(ctl_ncell)) deallocate (ctl_ncell)
  nctl = 0
end subroutine ctl_free

END MODULE obsope_tools_ctl
