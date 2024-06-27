program main
use common_ncio
implicit real(a-h,o-z)

real(4),allocatable::axlon(:,:),axlat(:,:),axz(:),pres(:,:,:)

integer,parameter::nelm=3
integer,parameter::elms(nelm)=(/2819,2820,3073/) !! U,V,T 
real(4),parameter::errs(nelm)=(/3.0,3.0,1.0/)    !! U,V,T 

integer,parameter::intv_x=4
integer,parameter::intv_y=4
integer,parameter::intv_z=2

real(4)::wk(8)
character(len=200)::cfile
character(len=200)::ncfile_in='history_merge.pe000000.nc'

integer::ncid, vidlon, vidlat,vidz

  call ncio_open( trim(ncfile_in), nf90_nowrite, ncid )
  call ncio_read_dim(ncid,"x",nlon)
  call ncio_read_dim(ncid,"y",nlat)
  call ncio_read_dim(ncid,"z",nlev)

  allocate(pres(nlon,nlat,nlev))
  allocate(axlon(nlon,nlat))
  allocate(axlat(nlon,nlat))
  allocate(axz(nlev))

  call ncio_read_const(ncid, "lon", nlon, nlat, axlon)
  call ncio_read_const(ncid, "lat", nlon, nlat, axlat)
  call ncio_read_const(ncid, "z", nlev, axz)
  call ncio_close( ncid ) 

cfile="test_obs_3d_xyz.dat"

open (21, file=trim(cfile), form='unformatted', access='sequential', convert='big_endian')

do ilon=1,nlon,intv_x
do ilat=1,nlat,intv_y
do ilev=1,nlev,intv_z
do ie=1,nelm
  wk(1)=real(elms(ie))  
  wk(2)=axlon(ilon,ilat)
  wk(3)=axlat(ilon,ilat)
  wk(4)=axz(iz)
  wk(5)=10.0  !!! dat
  wk(6)=errs(ie)   !!! err 
  wk(7)=1.0  !!! typ ADPUPA
  wk(8)=0.0   !!! dif
  write(21,iostat=ios) wk(1:8)
end do
!  write(*,'(F6.1,5F14.4)') wk(1:6)
end do
end do
end do

close(21)

stop
end program main
module common_ncio
!=======================================================================
!
! [PURPOSE:] NetCDF I/O
!
! [HISTORY:]
!   07/24/2014 Guo-Yuan Lien  created
!   .......... See git history for the following revisions
!
!=======================================================================
  use netcdf

  implicit none
  public

  INTEGER,PARAMETER :: r_dble=kind(0.0d0)
  INTEGER,PARAMETER :: r_sngl=kind(0.0e0)
  INTEGER,PARAMETER :: r_size=r_sngl

  interface ncio_read_const
    module procedure ncio_read_const_1d_r4
    module procedure ncio_read_const_2d_r4
    module procedure ncio_read_const_1d_r8
    module procedure ncio_read_const_2d_r8
  end interface ncio_read_const

  interface ncio_read
    module procedure ncio_read_1d_r4
    module procedure ncio_read_2d_r4
    module procedure ncio_read_3d_r4
    module procedure ncio_read_1d_r8
    module procedure ncio_read_2d_r8
    module procedure ncio_read_3d_r8
  end interface ncio_read

  interface ncio_write
    module procedure ncio_write_1d_r4
    module procedure ncio_write_2d_r4
    module procedure ncio_write_3d_r4
    module procedure ncio_write_1d_r8
    module procedure ncio_write_2d_r8
    module procedure ncio_write_3d_r8
  end interface ncio_write

contains

!-----------------------------------------------------------------------
! Check the status
!-----------------------------------------------------------------------
subroutine ncio_check(status)
  implicit none
  integer, intent(in) :: status

  if (status /= nf90_noerr) then
    write (6,*) trim(nf90_strerror(status))
    stop 10
  end if
end subroutine ncio_check
!-----------------------------------------------------------------------
! Open a netcdf file
!-----------------------------------------------------------------------
subroutine ncio_open(filename, mode, ncid)
  implicit none
  character(len=*), intent(in) :: filename
  integer, intent(in) :: mode
  integer, intent(out) :: ncid

  call ncio_check(nf90_open(filename, mode, ncid))
end subroutine ncio_open
!-----------------------------------------------------------------------
! Create a netcdf file
!-----------------------------------------------------------------------
subroutine ncio_create( filename, mode, ncid )
  implicit none
  character(len=*), intent(in) :: filename
  integer, intent(in) :: mode
  integer, intent(out) :: ncid

  call ncio_check( nf90_create( filename, mode, ncid ) )
end subroutine ncio_create
!-----------------------------------------------------------------------
! Close a netcdf file
!-----------------------------------------------------------------------
subroutine ncio_close(ncid)
  implicit none
  integer, intent(in) :: ncid

  call ncio_check(nf90_close(ncid))
end subroutine ncio_close
!-----------------------------------------------------------------------
! Read netcdf dimension
!-----------------------------------------------------------------------
subroutine ncio_read_dim(ncid, dimname, dimlen)
  implicit none
  integer, intent(in) :: ncid
  character(len=*), intent(in) :: dimname
  integer, intent(out) :: dimlen
  integer :: dimid

  call ncio_check(nf90_inq_dimid(ncid, dimname, dimid))
  call ncio_check(nf90_inquire_dimension(ncid, dimid, len=dimlen))
end subroutine ncio_read_dim
!-----------------------------------------------------------------------
! Read netcdf integer global attribute
!-----------------------------------------------------------------------
!subroutine ncio_read_gattr_i(ncid, attrname, attr)
!  implicit none
!  integer, intent(in) :: ncid
!  character(len=*), intent(in) :: attrname
!  integer, intent(out) :: attr

!  call ncio_check(nf90_get_att(ncid, nf90_global, attrname, attr))
!end subroutine ncio_read_gattr_i
!-----------------------------------------------------------------------
! Read netcdf single-precision global attribute
!-----------------------------------------------------------------------
subroutine ncio_read_gattr_r4(ncid, attrname, attr)
  implicit none
  integer, intent(in) :: ncid
  character(len=*), intent(in)  :: attrname
  real(r_sngl), intent(out) :: attr

  call ncio_check(nf90_get_att(ncid, nf90_global, attrname, attr))
end subroutine ncio_read_gattr_r4
!-----------------------------------------------------------------------
! Read netcdf double-precision global attribute
!-----------------------------------------------------------------------
subroutine ncio_read_gattr_r8(ncid, attrname, attr)
  implicit none
  integer, intent(in) :: ncid
  character(len=*), intent(in)  :: attrname
  real(r_dble), intent(out) :: attr

  call ncio_check(nf90_get_att(ncid, nf90_global, attrname, attr))
end subroutine ncio_read_gattr_r8
!-----------------------------------------------------------------------
! Read netcdf single-precision 1-D constant variable
!-----------------------------------------------------------------------
subroutine ncio_read_const_1d_r4(ncid, varname, dim1, var)
  implicit none
  integer, intent(in) :: ncid
  character(len=*), intent(in) :: varname
  integer, intent(in) :: dim1
  real(r_sngl), intent(out) :: var(dim1)
  integer :: varid

  call ncio_check(nf90_inq_varid(ncid, varname, varid))
  call ncio_check(nf90_get_var(ncid, varid, var,   &
                               start = (/ 1 /), &
                               count = (/ dim1 /)))
end subroutine ncio_read_const_1d_r4
!-----------------------------------------------------------------------
! Read netcdf single-precision 2-D variable
!-----------------------------------------------------------------------
subroutine ncio_read_const_2d_r4(ncid, varname, dim1, dim2, var)
  implicit none
  integer, intent(in) :: ncid
  character(len=*), intent(in) :: varname
  integer, intent(in) :: dim1, dim2
  real(r_sngl), intent(out) :: var(dim1,dim2)
  integer :: varid

  call ncio_check(nf90_inq_varid(ncid, varname, varid))
  call ncio_check(nf90_get_var(ncid, varid, var,      &
                               start = (/ 1, 1 /), &
                               count = (/ dim1, dim2 /)))
end subroutine ncio_read_const_2d_r4
!-----------------------------------------------------------------------
! Read netcdf single-precision 1-D variable
!-----------------------------------------------------------------------
subroutine ncio_read_1d_r4(ncid, varname, dim1, t, var)
  implicit none
  integer, intent(in) :: ncid
  character(len=*), intent(in) :: varname
  integer, intent(in) :: dim1, t
  real(r_sngl), intent(out) :: var(dim1)
  integer :: varid

  call ncio_check(nf90_inq_varid(ncid, varname, varid))
  call ncio_check(nf90_get_var(ncid, varid, var,   &
                               start = (/ 1, t /), &
                               count = (/ dim1, 1 /)))
end subroutine ncio_read_1d_r4
!-----------------------------------------------------------------------
! Read netcdf single-precision 2-D variable
!-----------------------------------------------------------------------
subroutine ncio_read_2d_r4(ncid, varname, dim1, dim2, t, var)
  implicit none
  integer, intent(in) :: ncid
  character(len=*), intent(in) :: varname
  integer, intent(in) :: dim1, dim2, t
  real(r_sngl), intent(out) :: var(dim1,dim2)
  integer :: varid

  call ncio_check(nf90_inq_varid(ncid, varname, varid))
  call ncio_check(nf90_get_var(ncid, varid, var,      &
                               start = (/ 1, 1, t /), &
                               count = (/ dim1, dim2, 1 /)))
end subroutine ncio_read_2d_r4
!-----------------------------------------------------------------------
! Read netcdf single-precision 3-D variable
!-----------------------------------------------------------------------
subroutine ncio_read_3d_r4(ncid, varname, dim1, dim2, dim3, t, var)
  implicit none
  integer, intent(in) :: ncid
  character(len=*), intent(in) :: varname
  integer, intent(in) :: dim1, dim2, dim3, t
  real(r_sngl), intent(out) :: var(dim1,dim2,dim3)
  integer :: varid

  call ncio_check(nf90_inq_varid(ncid, varname, varid))
  call ncio_check(nf90_get_var(ncid, varid, var,         &
                               start = (/ 1, 1, 1, t /), &
                               count = (/ dim1, dim2, dim3, 1 /)))
end subroutine ncio_read_3d_r4
!-----------------------------------------------------------------------
! Read netcdf double-precision 1-D variable
!-----------------------------------------------------------------------
subroutine ncio_read_const_1d_r8(ncid, varname, dim1, var)
  implicit none
  integer, intent(in) :: ncid
  character(len=*), intent(in) :: varname
  integer, intent(in) :: dim1
  real(r_dble), intent(out) :: var(dim1)
  integer :: varid

  call ncio_check(nf90_inq_varid(ncid, varname, varid))
  call ncio_check(nf90_get_var(ncid, varid, var,   &
                               start = (/ 1 /), &
                               count = (/ dim1 /)))
end subroutine ncio_read_const_1d_r8
!-----------------------------------------------------------------------
! Read netcdf double-precision 2-D variable
!-----------------------------------------------------------------------
subroutine ncio_read_const_2d_r8(ncid, varname, dim1, dim2, var)
  implicit none
  integer, intent(in) :: ncid
  character(len=*), intent(in) :: varname
  integer, intent(in) :: dim1, dim2
  real(r_dble), intent(out) :: var(dim1,dim2)
  integer :: varid

  call ncio_check(nf90_inq_varid(ncid, varname, varid))
  call ncio_check(nf90_get_var(ncid, varid, var,      &
                               start = (/ 1, 1 /), &
                               count = (/ dim1, dim2 /)))
end subroutine ncio_read_const_2d_r8
!-----------------------------------------------------------------------
! Read netcdf double-precision 1-D variable
!-----------------------------------------------------------------------
subroutine ncio_read_1d_r8(ncid, varname, dim1, t, var)
  implicit none
  integer, intent(in) :: ncid
  character(len=*), intent(in) :: varname
  integer, intent(in) :: dim1, t
  real(r_dble), intent(out) :: var(dim1)
  integer :: varid

  call ncio_check(nf90_inq_varid(ncid, varname, varid))
  call ncio_check(nf90_get_var(ncid, varid, var,   &
                               start = (/ 1, t /), &
                               count = (/ dim1, 1 /)))
end subroutine ncio_read_1d_r8
!-----------------------------------------------------------------------
! Read netcdf double-precision 2-D variable
!-----------------------------------------------------------------------
subroutine ncio_read_2d_r8(ncid, varname, dim1, dim2, t, var)
  implicit none
  integer, intent(in) :: ncid
  character(len=*), intent(in) :: varname
  integer, intent(in) :: dim1, dim2, t
  real(r_dble), intent(out) :: var(dim1,dim2)
  integer :: varid

  call ncio_check(nf90_inq_varid(ncid, varname, varid))
  call ncio_check(nf90_get_var(ncid, varid, var,      &
                               start = (/ 1, 1, t /), &
                               count = (/ dim1, dim2, 1 /)))
end subroutine ncio_read_2d_r8
!-----------------------------------------------------------------------
! Read netcdf double-precision 3-D variable
!-----------------------------------------------------------------------
subroutine ncio_read_3d_r8(ncid, varname, dim1, dim2, dim3, t, var)
  implicit none
  integer, intent(in) :: ncid
  character(len=*), intent(in) :: varname
  integer, intent(in) :: dim1, dim2, dim3, t
  real(r_dble), intent(out) :: var(dim1,dim2,dim3)
  integer :: varid

  call ncio_check(nf90_inq_varid(ncid, varname, varid))
  call ncio_check(nf90_get_var(ncid, varid, var,         &
                               start = (/ 1, 1, 1, t /), &
                               count = (/ dim1, dim2, dim3, 1 /)))
end subroutine ncio_read_3d_r8
!-----------------------------------------------------------------------
! Read netcdf text variable
!-----------------------------------------------------------------------
subroutine ncio_read_text(ncid, varname, length, t, var)
  implicit none
  integer, intent(in) :: ncid
  character(len=*), intent(in) :: varname
  integer, intent(in) :: length, t
  character(len=length), intent(out) :: var
  integer :: varid

  call ncio_check(nf90_inq_varid(ncid, varname, varid))
  call ncio_check(nf90_get_var(ncid, varid, var,   &
                               start = (/ 1, t /), &
                               count = (/ length, 1 /)))
end subroutine ncio_read_text
!-----------------------------------------------------------------------
! Write netcdf single-precision 1-D variable
!-----------------------------------------------------------------------
subroutine ncio_write_1d_r4(ncid, varname, dim1, t, var)
  implicit none
  integer, intent(in) :: ncid
  character(len=*), intent(in) :: varname
  integer, intent(in) :: dim1, t
  real(r_sngl), intent(in) :: var(dim1)
  integer :: varid

  call ncio_check(nf90_inq_varid(ncid, varname, varid))
  call ncio_check(nf90_put_var(ncid, varid, var,   &
                               start = (/ 1, t /), &
                               count = (/ dim1, 1 /)))
end subroutine ncio_write_1d_r4
!-----------------------------------------------------------------------
! Write netcdf single-precision 2-D variable
!-----------------------------------------------------------------------
subroutine ncio_write_2d_r4(ncid, varname, dim1, dim2, t, var)
  implicit none
  integer, intent(in) :: ncid
  character(len=*), intent(in) :: varname
  integer, intent(in) :: dim1, dim2, t
  real(r_sngl), intent(in) :: var(dim1,dim2)
  integer :: varid

  call ncio_check(nf90_inq_varid(ncid, varname, varid))
  call ncio_check(nf90_put_var(ncid, varid, var,      &
                               start = (/ 1, 1, t /), &
                               count = (/ dim1, dim2, 1 /)))
end subroutine ncio_write_2d_r4
!-----------------------------------------------------------------------
! Write netcdf single-precision 3-D variable
!-----------------------------------------------------------------------
subroutine ncio_write_3d_r4(ncid, varname, dim1, dim2, dim3, t, var)
  implicit none
  integer, intent(in) :: ncid
  character(len=*), intent(in) :: varname
  integer, intent(in) :: dim1, dim2, dim3, t
  real(r_sngl), intent(in) :: var(dim1,dim2,dim3)
  integer :: varid

  call ncio_check(nf90_inq_varid(ncid, varname, varid))
  call ncio_check(nf90_put_var(ncid, varid, var,         &
                               start = (/ 1, 1, 1, t /), &
                               count = (/ dim1, dim2, dim3, 1 /)))
end subroutine ncio_write_3d_r4
!-----------------------------------------------------------------------
! Write netcdf double-precision 1-D variable
!-----------------------------------------------------------------------
subroutine ncio_write_1d_r8(ncid, varname, dim1, t, var)
  implicit none
  integer, intent(in) :: ncid
  character(len=*), intent(in) :: varname
  integer, intent(in) :: dim1, t
  real(r_dble), intent(in) :: var(dim1)
  integer :: varid

  call ncio_check(nf90_inq_varid(ncid, varname, varid))
  call ncio_check(nf90_put_var(ncid, varid, var,   &
                               start = (/ 1, t /), &
                               count = (/ dim1, 1 /)))
end subroutine ncio_write_1d_r8
!-----------------------------------------------------------------------
! Write netcdf double-precision 2-D variable
!-----------------------------------------------------------------------
subroutine ncio_write_2d_r8(ncid, varname, dim1, dim2, t, var)
  implicit none
  integer, intent(in) :: ncid
  character(len=*), intent(in) :: varname
  integer, intent(in) :: dim1, dim2, t
  real(r_dble), intent(in) :: var(dim1,dim2)
  integer :: varid

  call ncio_check(nf90_inq_varid(ncid, varname, varid))
  call ncio_check(nf90_put_var(ncid, varid, var,      &
                               start = (/ 1, 1, t /), &
                               count = (/ dim1, dim2, 1 /)))
end subroutine ncio_write_2d_r8
!-----------------------------------------------------------------------
! Write netcdf double-precision 3-D variable
!-----------------------------------------------------------------------
subroutine ncio_write_3d_r8(ncid, varname, dim1, dim2, dim3, t, var)
  implicit none
  integer, intent(in) :: ncid
  character(len=*), intent(in) :: varname
  integer, intent(in) :: dim1, dim2, dim3, t
  real(r_dble), intent(in) :: var(dim1,dim2,dim3)
  integer :: varid

  call ncio_check(nf90_inq_varid(ncid, varname, varid))
  call ncio_check(nf90_put_var(ncid, varid, var,         &
                               start = (/ 1, 1, 1, t /), &
                               count = (/ dim1, dim2, dim3, 1 /)))
end subroutine ncio_write_3d_r8
!-----------------------------------------------------------------------
! Write netcdf text variable
!-----------------------------------------------------------------------
subroutine ncio_write_text (ncid, varname, length, t, var)
  implicit none
  integer, intent(in) :: ncid
  character(len=*), intent(in) :: varname
  integer, intent(in) :: length, t
  character(len=length), intent(in) :: var
  integer :: varid

  call ncio_check(nf90_inq_varid(ncid, varname, varid))
  call ncio_check(nf90_put_var(ncid, varid, var,   &
                               start = (/ 1, t /), &
                               count = (/ length, 1 /)))
end subroutine ncio_write_text

end module common_ncio
