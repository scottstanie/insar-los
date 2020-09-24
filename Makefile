FC = gfortran
CXX = g++
FCFLAGS = -fbounds-check -ffixed-line-length-132 -fopenmp -fPIC
CXXFLAGS = -std=c++11 -Wall -Wextra -fopenmp 
# Note: -Wl,option1,option2 passes  "option1 option2" to the linker
# https://stackoverflow.com/questions/6562403/i-dont-understand-wl-rpath-wl
LDLIBS = -lsqlite3 -lm -lgfortran 

# Add path to include directory for gdal (and other anaconda libraries)
CXXFLAGS += ${shell gdal-config --cflags}
# add flags for -l and -L paths
LDLIBS += ${shell gdal-config --libs}
# The above takes care of this manual lib path:
# LIBPATH = -L/home/scott/miniconda3/envs/mapping/lib/ 
# Add the gdal dependencies using the relative path for the linker
# for me: /home/scott/miniconda3/envs/mapping/lib
LIBDIR = ${shell gdal-config --prefix}/lib
#
LDLIBS += -Wl,-rpath,$(LIBDIR)
# This doesn't seem to work with all deps... still says "use --rpath"
# LDLIBS += ${shell gdal-config --dep-libs}


# SRC_DIR = src  # If we move to storing the .f90 files separately
# SRCS = $(wildcard $(SRC_DIR)/*.f90) 
SRCS = $(wildcard *.f90)
# OBJECTS = $(SRCS:.f90=.o) # If we want 1 object per file
OBJECTS = create_los_map.o orbithermite.o orbitrangetime.o intp_orbit.o

# These are the files for which there was a build* file
TARGETS = create_los_map # intp_orbit_lib orbitrangetime_lib

all:  $(TARGETS)

create_los_map:  $(OBJECTS) $(SRCS)
	@echo here is my LIBDIR $(LIBDIR), which should contain libgdal.so
	$(CXX) $(CXXFLAGS)  -o $@ $(OBJECTS) $(LDLIBS)

create_los_map.o: create_los_map.cc
	$(CXX) $(CXXFLAGS) -c $< $(LIBPATH) $(LDLIBS)

orbithermite.o: orbithermite.f
	$(FC) $(FCFLAGS) -c $<

orbitrangetime.o: orbitrangetime.f90
	$(FC) $(FCFLAGS) -c $<

intp_orbit.o: intp_orbit.f90
	$(FC) $(FCFLAGS) -c $<


.PHONY: clean ext


clean:
	rm -f *.o 
	rm -f $(TARGETS)

