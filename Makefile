FC = gfortran
CXX = g++
FCFLAGS = -fbounds-check -ffixed-line-length-132 -fopenmp -fPIC
CXXFLAGS = -std=c++11 -Wall -Wextra -fopenmp 

# Add path to include directory for gdal (and other anaconda libraries)
CXXFLAGS += ${shell gdal-config --cflags}
# add flags for -l and -L paths
# The above takes care of this manual lib path:
# LIBPATH = -L/home/scott/miniconda3/envs/mapping/lib/ 
# Add the gdal dependencies using the relative path for the linker
# for me: /home/scott/miniconda3/envs/mapping/lib
# Note: -Wl,option1,option2 passes  "option1 option2" to the linker
# https://stackoverflow.com/questions/6562403/i-dont-understand-wl-rpath-wl
LDLIBS = -lgfortran 
LDLIBS += ${shell gdal-config --libs}

LIBDIR = ${shell gdal-config --prefix}/lib
LDLIBS += -Wl,-rpath,$(LIBDIR)
# This doesn't seem to work with all deps... still says "use --rpath"
# LDLIBS += ${shell gdal-config --dep-libs}

# TODO: figure out mac? 
# https://stackoverflow.com/questions/43555410/enable-openmp-support-in-clang-in-mac-os-x-sierra-mojave


SRC_DIR = src
BUILD_DIR = build
$(shell mkdir -p $(BUILD_DIR))
# SRCS = $(wildcard $(SRC_DIR)/*.f90) 
# SRCS = $(wildcard *.f90)

# OBJECTS = $(SRCS:.f90=.o) # If we want 1 object per file
OBJECTS = $(BUILD_DIR)/create_los_map.o $(BUILD_DIR)/orbithermite.o 
OBJECTS += $(BUILD_DIR)/orbitrangetime.o $(BUILD_DIR)/intp_orbit.o

TARGET = $(BUILD_DIR)/create_los_map
all:  $(TARGET)


# Reminder: $@ is the target name, $^ is the name of all prerequisites
$(TARGET):  $(OBJECTS)
	@echo here is my LIBDIR $(LIBDIR), which should contain libgdal.so
	$(CXX) $(CXXFLAGS) -o $@ $(OBJECTS) $(LDLIBS)

$(BUILD_DIR)/create_los_map.o: $(SRC_DIR)/create_los_map.cc
	$(CXX) $(CXXFLAGS) -c $^ -o $@ $(LIBPATH) $(LDLIBS)

$(BUILD_DIR)/orbithermite.o: $(SRC_DIR)/orbithermite.f
	$(FC) $(FCFLAGS) -c $^ -o $@

$(BUILD_DIR)/orbitrangetime.o: $(SRC_DIR)/orbitrangetime.f90
	$(FC) $(FCFLAGS) -c $^ -o $@

$(BUILD_DIR)/intp_orbit.o: $(SRC_DIR)/intp_orbit.f90
	$(FC) $(FCFLAGS) -c $^ -o $@


.PHONY: clean

clean:
	rm -rf $(BUILD_DIR)
	# rm -f $(TARGET)

