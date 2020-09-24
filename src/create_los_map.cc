/*
 * Create 3 files (los_east.bin, los_north.bin, los_up.bin) 
 * of maps of the line of sight unit vectors from satellite to ground
 * 
*/

#include <gdal.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>
#include "cpl_conv.h"  // for CPLMalloc()
#include "gdal_priv.h"

const double pi = 4.0 * atan2(1., 1.);
const double deg2rad = pi / 180.;
const double a = 6378137.0;
const double e2 = 0.0066943799901499996;

const char *OUT_EAST{"los_east.bin"};
const char *OUT_NORTH{"los_north.bin"};
const char *OUT_UP{"los_up.bin"};

// Fortran function declarations:
/* 
 * xyz_ground is 3-vector of point on the ground surface
 * thist, xhist, vhist are satellite orbit history matrices
 * tguess, satxguess, satvguess are initial guesses for time, position, velo
 * tout, rangeout are the output/solutions for orbit time, range
 */
extern "C" void orbitrangetime_(double *xyz_ground, double *thist, double *xhist, double *vhist, int *numstatevec,
                                double *tguess, double *satxguess, double *satvguess,
                                double *tout, double *rangeout);
extern "C" int intp_orbit_(double *thist, double *xhist, double *vhist, int *numstatevec, double *time,
                           double *xyz_out, double *vel_out);
// extern "C" void orbithermite_(double *xhist, double *vhist, double *thist, double *t_in,
//                               double *x_out, double *v_out);

/* Store the data from .orbtiming file containing satellite orbit state into tvec, xvec, vvec */
void read_orbit_state(const std::string filename, std::vector<double> &tvec, std::vector<double> &xvec,
                      std::vector<double> &vvec) {
  // $ head precise_orbtiming
  // 0
  // 0
  // 0
  // 3992
  // 46472.0 -776354.893210 -5764729.554489 4020703.265768 -2269.808392 -3946.433388 -6078.542538 0.0 0.0 0.0
  // 46482.0 -799037.646611 -5803853.456535 3959691.929673 -2266.683274 -3878.274472 -6123.610014 0.0 0.0 0.0
  std::ifstream fs;
  fs.open(filename);
  if (!fs.is_open()) {
    std::cerr << "Failed to open " << filename << std::endl;
    return;
  }
  // first 3 lines are usually zeros
  int tmp;
  fs >> tmp;
  fs >> tmp;
  fs >> tmp;

  int num_states{};
  fs >> num_states;
  std::cout << "num orbit states: " << num_states << std::endl;
  tvec.resize(num_states);
  xvec.resize(3 * num_states);
  vvec.resize(3 * num_states);

  for (int i = 0; i < num_states; i++) {
    double t, x, y, z, vx, vy, vz, ax, ay, az;
    fs >> t >> x >> y >> z >> vx >> vy >> vz >> ax >> ay >> az;
    tvec[i] = t;
    xvec[3 * i] = x;
    xvec[3 * i + 1] = y;
    xvec[3 * i + 2] = z;
    vvec[3 * i] = vx;
    vvec[3 * i + 1] = vy;
    vvec[3 * i + 2] = vz;
  }
  fs.close();
  return;
}

/* Given a LLH tuple (latd, lond, hgt), convert to geocentric XYZ coordinates, store in xyz_out */
void get_ground_xyz(const double latd, const double lond, const double hgt, double *xyz_out) {
  double lat = latd * deg2rad;
  double lon = lond * deg2rad;
  double re = a / sqrt(1.0 - e2 * sin(lat) * sin(lat));

  xyz_out[0] = (re + hgt) * cos(lat) * cos(lon);
  xyz_out[1] = (re + hgt) * cos(lat) * sin(lon);
  xyz_out[2] = (re - (re * e2) + hgt) * sin(lat);
}

/* Convert a relative (difference) vector in ECEF coords to ENU
 * based on https://gist.github.com/govert/1b373696c9a27ff4c72a
 */
void ecef_to_enu(const double *xyz, const double latd0, const double lond0, double *outEnu) {
  // Convert to radians in notation consistent with the paper:
  double x{xyz[0]}, y{xyz[1]}, z{xyz[2]};
  double lat = latd0 * deg2rad;
  double lon = lond0 * deg2rad;

  double sin_lat = sin(lat);
  double cos_lat = cos(lat);
  double cos_lon = cos(lon);
  double sin_lon = sin(lon);

  // This is the matrix multiplication
  outEnu[0] = -sin_lon * x + cos_lon * y;
  outEnu[1] = -cos_lon * sin_lat * x - sin_lat * sin_lon * y + cos_lat * z;
  outEnu[2] = cos_lat * cos_lon * x + cos_lat * sin_lon * y + sin_lat * z;
}

/* Main function to create the map given an orbtiming_filename and dem_filename
 * Writes output to files OUT_EAST, OUT_NORTH, and OUT_UP
 */
void create_map(std::string orbtiming_filename, std::string dem_filename) {
  // Read and store orbit state information
  std::cout << "reading " << orbtiming_filename << std::endl;

  std::vector<double> tvec;
  std::vector<double> xvec;
  std::vector<double> vvec;
  read_orbit_state(orbtiming_filename, tvec, xvec, vvec);
  int num_states = tvec.size();
  double *thist = tvec.data();
  double *xhist = xvec.data();
  double *vhist = vvec.data();

  double t0 = thist[0];
  double x0[3] = {xhist[0], xhist[1], xhist[2]};
  double v0[3] = {vhist[0], vhist[1], vhist[2]};
  //

  // Find the list of all lat/lon/height from the DEM dataset
  GDALAllRegister();
  GDALDataset *poDemDataset;
  poDemDataset = static_cast<GDALDataset *>(GDALOpen(dem_filename.c_str(), GA_ReadOnly));
  if (poDemDataset == nullptr) {
    std::cerr << "Failed to open DEM dataset " << dem_filename << std::endl;
    return;
  }

  int xSize = poDemDataset->GetRasterXSize();
  int ySize = poDemDataset->GetRasterYSize();
  double adfGeoTransform[6];
  if (poDemDataset->GetGeoTransform(adfGeoTransform) != CE_None) {
    std::cerr << "Failed to get Geo Transform" << std::endl;
    return;
  }
  double xStart = adfGeoTransform[0];
  double xStep = adfGeoTransform[1];
  double yStart = adfGeoTransform[3];
  double yStep = adfGeoTransform[5];
  // Read in the DEM height data
  short *heights = new short[ySize * xSize];
  GDALRasterBand *poBand = poDemDataset->GetRasterBand(1);
  CPLErr readErr = poBand->RasterIO(GF_Read, 0, 0, xSize, ySize, heights, xSize, ySize, GDT_Int16, 0, 0);
  if (readErr != 0) {
    std::cerr << "Failed to read in dataset 1 of " << dem_filename << std::endl;
    return;
  }

  // Allocated binary arrays of output
  float *los_east = new float[ySize * xSize];
  float *los_north = new float[ySize * xSize];
  float *los_up = new float[ySize * xSize];
  std::cout << "Looping over (rows, cols) = (" << ySize << "," << xSize << ") ("
            << xSize * ySize << " total pixels)" << std::endl;

// LLH loop:
#pragma omp parallel for shared(heights, los_east, los_north, los_up, thist, xhist, vhist, num_states, t0, x0, v0)
  for (int xi = 0; xi < xSize; xi++) {
    for (int yi = 0; yi < ySize; yi++) {
      double cur_lond = xStart + xStep * xi;
      double cur_latd = yStart + yStep * yi;
      size_t idx2d = yi * xSize + xi;
      double cur_h0 = static_cast<double>(heights[idx2d]);
      double xyz_ground[3]{};
      get_ground_xyz(cur_latd, cur_lond, cur_h0, xyz_ground);

      // Find the time (and range) associated with the satellite point t0, x0, v0
      double tout{}, rangeout{};
      orbitrangetime_(xyz_ground, thist, xhist, vhist, &num_states, &t0, x0, v0, &tout, &rangeout);

      // Interpolate the orbit to the exact time found
      double xyz_out[3]{}, vel_out[3]{};
      intp_orbit_(thist, xhist, vhist, &num_states, &tout, xyz_out, vel_out);

      // Get the unit vector from satellite to ground
      double dr[3] = {
          (xyz_ground[0] - xyz_out[0]) / rangeout,
          (xyz_ground[1] - xyz_out[1]) / rangeout,
          (xyz_ground[2] - xyz_out[2]) / rangeout};

      // Rotate unit vec from ECEF to ENU0
      double dr_enu[3]{};
      ecef_to_enu(dr, cur_latd, cur_lond, dr_enu);
      los_east[idx2d] = dr_enu[0];
      los_north[idx2d] = dr_enu[1];
      los_up[idx2d] = dr_enu[2];
    }
  }  // end LLH loop

  // GDAL translating occurs in python wrapper
  FILE *fout = fopen(OUT_EAST, "wb");
  fwrite(los_east, sizeof(float), xSize * ySize, fout);
  fclose(fout);
  fout = fopen(OUT_EAST, "wb");
  fwrite(los_north, sizeof(float), xSize * ySize, fout);
  fclose(fout);
  fout = fopen(OUT_EAST, "wb");
  fwrite(los_up, sizeof(float), xSize * ySize, fout);
  fclose(fout);

  delete[] heights;
  delete[] los_east;
  delete[] los_north;
  delete[] los_up;
}

int main(int argc, char *argv[]) {
  if (argc < 2) {
    std::cerr << "Usage: " << argv[0] << " orbtiming_filename dem_filename" << std::endl;
    return 1;
  }
  std::string orbtiming_filename = argv[1];
  std::string dem_filename = argv[2];
  create_map(orbtiming_filename, dem_filename);
  return 0;
}
