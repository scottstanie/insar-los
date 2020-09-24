#!/usr/bin/env python
import sys
import os
from datetime import datetime


def readxmlparam(xmllines, param):
    for line in xmllines:
        if param in line:
            i = line.find(param)
            str1 = line[i:]
            istart = str1.find('>') + 1
            istop = str1.find('<')
            value = str1[istart:istop]
            # print line[i:],'\n'
            # print istart, istop, '\n'
            return value


def timeinseconds(timestring):
    #    dt = datetime.strptime(timestring, 'TAI=%Y-%m-%dT%H:%M:%S.%f')
    dt = datetime.strptime(timestring, 'UTC=%Y-%m-%dT%H:%M:%S.%f')
    #    dt = datetime.strptime(timestring, 'UT1=%Y-%m-%dT%H:%M:%S.%f')
    secs = dt.hour * 3600 + dt.minute * 60 + dt.second + dt.microsecond / 1000000.0
    return secs


def parse_orbit():
    #  create an orbtiming file for all bursts (1-11) using a precise orbit file
    if len(sys.argv) < 2:
        print('Usage: precise_orbit_burst.py preciseorbitfile')
        sys.exit(1)

    orbitfile = sys.argv[1]

    # read the precise file
    xmlfile = open(orbitfile, 'r')
    xmllines = xmlfile.readlines()
    xmlfile.close()

    #  save orbit and timing information

    #  extract each state vector
    start = []
    stop = []
    for i in range(len(xmllines)):
        if '<OSV>' in xmllines[i]:
            start.append(i)

        if '</OSV>' in xmllines[i]:
            stop.append(i)

    time = []
    x = []
    y = []
    z = []
    vx = []
    vy = []
    vz = []
    for i in range(len(start)):
        statelines = xmllines[start[i]:stop[i]]
        time.append(readxmlparam(statelines, 'UTC'))
        x.append(readxmlparam(statelines, 'X unit'))
        y.append(readxmlparam(statelines, 'Y unit'))
        z.append(readxmlparam(statelines, 'Z unit'))
        vx.append(readxmlparam(statelines, 'VX unit'))
        vy.append(readxmlparam(statelines, 'VY unit'))
        vz.append(readxmlparam(statelines, 'VZ unit'))

    orbinfo = open('orbtiming.full', 'w')
    orbinfo.write('0 \n')
    orbinfo.write('0 \n')
    orbinfo.write('0 \n')
    orbinfo.write(str(len(start)) + '\n')
    for i in range(len(start)):
        orbinfo.write(
            str(timeinseconds(time[i])) + ' ' + str(x[i]) + ' ' + str(y[i]) + ' ' + str(z[i]) +
            ' ' + str(vx[i]) + ' ' + str(vy[i]) + ' ' + str(vz[i]) + ' 0.0 0.0 0.0')
        orbinfo.write('\n')

    orbinfo.close()


def save_as_vrt(filename, dem_filename, out_dtype="float32", outfile=None):
    """
    Save a VRT for raw binary files, using DEM geospatial into

    outfile, unless passed, will be `filename` + ".vrt"

    VRT options:
    SourceFilename: The name of the raw file containing the data for this band.
        The relativeToVRT attribute can be used to indicate if the
        SourceFilename is relative to the .vrt file (1) or not (0).
    ImageOffset: The offset in bytes to the beginning of the first pixel of
        data of this image band. Defaults to zero.
    PixelOffset: The offset in bytes from the beginning of one pixel and
        the next on the same line. In packed single band data this will be
        the size of the dataType in bytes.
    LineOffset: The offset in bytes from the beginning of one scanline of data
        and the next scanline of data. In packed single band data this will
        be PixelOffset * rasterXSize.

    Ref: https://gdal.org/drivers/raster/vrt.html#vrt-descriptions-for-raw-files
    """
    import gdal
    import numpy as np
    outfile = outfile or (filename + ".vrt")
    if outfile is None:
        raise ValueError("Need outfile or filename to save")

    # Get geotransform and project based on DEM file
    try:
        ds = gdal.Open(dem_filename)
        geotrans = ds.GetGeoTransform()
        srs = ds.GetSpatialRef()
        rows, cols = ds.RasterYSize, ds.RasterXSize
        # band = ds.GetRasterBand(1)
        # dtype = band.ReadAsArray(win_xsize=1, win_ysize=1).dtype
        # band = None
        ds = None
    except:
        print(f"Warning: Cant get geotransform from {dem_filename}")
        raise

    out_dtype = np.dtype(out_dtype)
    bytes_per_pix = out_dtype.itemsize
    num_bands = 1
    bandnum = 0
    # interleave = "BIP"  # Band interleaved by pixel
    image_offset = bandnum * bytes_per_pix
    pixel_offset = num_bands * bytes_per_pix
    line_offset = num_bands * cols * bytes_per_pix

    # Quick check that sizes and dtypes of files make sense
    total_bytes = os.path.getsize(filename)
    assert rows == int(
        total_bytes / bytes_per_pix / cols /
        num_bands), (f"rows = total_bytes / bytes_per_pix / cols / num_bands , but "
                     f"{rows} != {total_bytes} / {bytes_per_pix} / {cols} / {num_bands} ")

    # Create ouput VRT
    vrt_driver = gdal.GetDriverByName("VRT")

    out_raster = vrt_driver.Create(outfile, xsize=cols, ysize=rows, bands=0)
    out_raster.SetGeoTransform(geotrans)
    out_raster.SetProjection(srs.ExportToWkt())
    options = [
        'subClass=VRTRawRasterBand',
        # split, since relative to file, so remove directory name
        'SourceFilename={}'.format(os.path.split(filename)[1]),
        'relativeToVRT=1',  # location of file: make it relative to the VRT file
        'ImageOffset={}'.format(image_offset),
        'PixelOffset={}'.format(pixel_offset),
        'LineOffset={}'.format(line_offset),
        # 'ByteOrder=LSB'
    ]
    print(options)
    gdal_dtype = numpy_to_gdal_type(out_dtype)
    print("gdal dtype", gdal_dtype, out_dtype)
    out_raster.AddBand(gdal_dtype, options)
    out_raster = None  # Force write

    return


def numpy_to_gdal_type(np_dtype):
    from osgeo import gdal_array
    # Wrap in np.dtype in case string is passed
    return gdal_array.NumericTypeCodeToGDALTypeCode(np_dtype)
