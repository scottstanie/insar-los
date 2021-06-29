#!/usr/bin/env python
import os
from datetime import timedelta
import eof
import apertools.parsers


def create_orbtiming_file(args):
    if not args.sentinel_file:
        print("No Sentinel-1 file specifiy. Searching current directory.")
        parsed_sentinel = list(eof.download.find_unique_safes("."))[0]
    else:
        parsed_sentinel = apertools.parsers.Sentinel(args.sentinel_file)

    if not args.orbit_file:
        filenames = eof.download.main(
            sentinel_file=parsed_sentinel.filename,
            save_dir=args.orbit_save_dir,
        )
        orbit_file = filenames[0]
    else:
        orbit_file = args.orbit_file

    start_time = parsed_sentinel.start_time
    min_time = start_time - timedelta(minutes=30)
    max_time = start_time + timedelta(minutes=30)
    orbit_tuples = eof.parsing.parse_orbit(
        orbit_file, min_time=min_time, max_time=max_time
    )

    eof.parsing.write_orbinfo(orbit_tuples, outname=args.orbtiming_file)


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
    from osgeo import gdal
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
    assert rows == int(total_bytes / bytes_per_pix / cols / num_bands), (
        f"rows = total_bytes / bytes_per_pix / cols / num_bands , but "
        f"{rows} != {total_bytes} / {bytes_per_pix} / {cols} / {num_bands} "
    )

    # Create ouput VRT
    vrt_driver = gdal.GetDriverByName("VRT")

    out_raster = vrt_driver.Create(outfile, xsize=cols, ysize=rows, bands=0)
    out_raster.SetGeoTransform(geotrans)
    out_raster.SetProjection(srs.ExportToWkt())
    options = [
        "subClass=VRTRawRasterBand",
        # split, since relative to file, so remove directory name
        "SourceFilename={}".format(os.path.split(filename)[1]),
        "relativeToVRT=1",  # location of file: make it relative to the VRT file
        "ImageOffset={}".format(image_offset),
        "PixelOffset={}".format(pixel_offset),
        "LineOffset={}".format(line_offset),
        # 'ByteOrder=LSB'
    ]
    # print(options)
    gdal_dtype = numpy_to_gdal_type(out_dtype)
    # print("gdal dtype", gdal_dtype, out_dtype)
    out_raster.AddBand(gdal_dtype, options)
    out_raster = None  # Force write

    return


def numpy_to_gdal_type(np_dtype):
    from osgeo import gdal_array

    # Wrap in np.dtype in case string is passed
    return gdal_array.NumericTypeCodeToGDALTypeCode(np_dtype)
