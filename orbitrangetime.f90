      subroutine orbitrangetime(xyz,timeorbit,xx,vv,numstatevec,tline0,satx0,satv0,tline,range)

        implicit none

        !c  inputs
        real*8 xyz(3)                          !  point on ground
        real*8 timeorbit(*), xx(3,*), vv(3,*)  !  orbit state vectors
        real*8 tline0, satx0(3),satv0(3)       !  initial search point 
        !c  outputs
        real*8 tline,range                     !  solution for orbit time, range
        !c  internal variables
        real*8 satx(3),satv(3),tprev,dr(3),dopfact,fn,c1,c2,fnprime,BAD_VALUE
        real*8 rngpix
        integer k, stat, intp_orbit, numstatevec

        !f2py intent(in) :: xyz, timeorbit, xx, vv, tline0, satx0, satv0
        !f2py intent(out) tline, range

        BAD_VALUE=-999999.99999999d0

!!$        print *,xyz,timeorbit(1),xx(:,1)
!!$        print *,vv(:,1),numstatevec,tline0
!!$        print *,satx0,satv0

        !c  starting state
        tline = tline0
        satx = satx0
        satv = satv0
!!$        print *,tline,satx,satv
!!$        print *,'start satx v ',satx,satv

        do k=1,51!51
           tprev = tline  

           dr = xyz - satx
           rngpix = dsqrt(dot_product(dr,dr)) !norm2(dr)    

           dopfact = dot_product(dr,satv)
!!$            fdop = 0.5d0 * wvl * evalPoly1d_f(fdvsrng,rngpix)
!!$            fdopder = 0.5d0 * wvl * evalPoly1d_f(fddotvsrng,rngpix)

           fn = dopfact !- fdop * rngpix

           c1 = -dot_product(satv,satv) !(0.0d0 * dot(sata,dr) - dot(satv,satv))
           c2 = 0. !(fdop/rngpix + fdopder)

           fnprime = c1 + c2*dopfact

           tline = tline - fn / fnprime

           !!            print *, c1, c2, rngpix

!!$           print *,k,tline
           stat = intp_orbit(timeorbit,xx,vv,numstatevec,tline,satx,satv)

           if (stat.ne.0) then
              tline = BAD_VALUE
              rngpix = BAD_VALUE
              exit
           endif

!!!Check for convergence
           if (abs(tline - tprev).lt.5.0d-9) then
              !conv = conv + 1
              exit
           endif
        enddo  ! end iteration loop

!!$        print *,xyz, satx, tline
        dr = xyz - satx
        rngpix = dsqrt(dot_product(dr,dr)) !norm2(dr)
        range=rngpix
        !print *,'end   satx v ',satx,satv,rngpix,tline
!!$        print *,'tline rngpix ',tline,range
        return
      end subroutine orbitrangetime
