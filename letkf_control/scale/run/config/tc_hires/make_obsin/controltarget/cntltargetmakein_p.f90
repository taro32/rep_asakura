program main
use common_ncio
implicit real(a-h,o-z)

real(4),allocatable::axlon(:,:),axlat(:,:),axz(:),pres(:,:,:)

integer,parameter::nelm=1 !3
integer,parameter::elms(nelm)=(/14593/) !! Pres
real(4),parameter::errs(nelm)=(/2.0/)    !! Pres 1.0hPa-->10.0hPa 20241124 

integer,parameter::intv_x=4 !not used
integer,parameter::intv_y=4 !not used
integer,parameter::intv_z=2 !not used

real(4)::wk(8)
character(len=200)::cfile
character(len=200)::ncfile_in='../history.pe000000.nc'

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
  call ncio_read(ncid,"PRES",nlon,nlat,nlev,1,pres)
  call ncio_close( ncid ) 

cfile="controltarget_965_error2"

open (21, file=trim(cfile), form='unformatted', access='sequential') !, convert='big_endian')

!do ilon=1,nlon,intv_x
!do ilat=1,nlat,intv_y
!do ilev=1,nlev,intv_z
!do ie=1,nelm
ilon = int(nlon/2.0)
ilat = int(nlat/2.0)
ilev = 1
ie = 1
  print *, ilon, ilat, ilev, ie
  wk(1)=real(elms(ie))  
  wk(2)=axlon(ilon,ilat)
  wk(3)=axlat(ilon,ilat)
!  wk(4)=axz(iz)
  wk(4)=axz(ilev)
!  wk(4)=pres(ilon,ilat,ilev) * 0.01 !!! hPa
  print*, wk(4)
  wk(5)=96500 * 0.01 !100000 * 0.01  !!! dat [hPa]
  wk(6)=errs(ie)   !!! err 
  wk(7)=1.0  !!! typ ADPUPA
  wk(8)=0.0   !!! dif
  write(21,iostat=ios) wk(1:8)
!end do
  write(*,*) wk(1)
    write(*,*) wk(2)
      write(*,*) wk(3)
        write(*,*) wk(4)
          write(*,*) wk(5)
            write(*,*) wk(6)
              write(*,*) wk(7)
!end do
!end do
!end do

close(21)

stop
end program main
