#!/usr/bin/env python
import argparse
from datetime import timedelta
import glob
import os
import sys
import subprocess
import eof
import apertools.parsers
import utils


def get_cli_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--outfile",
        default="los_enu.tif",
        help="Name of final, merged file with 3 bands for east, north, and up LOS vectors "
        "(default = %(default)s)",
    )
    parser.add_argument(
        "--dem",
        default="elevation.dem",
        help="Filepath of target DEM. LOS file will match this grid. (default = %(default)s)",
    )
    parser.add_argument(
        "--sentinel-file",
        required=False,
        help="Name of .SAFE or .zip sentinel file to find LOS vector for",
    )
    parser.add_argument(
        "--orbit-file",
        required=False,
        help="Name of .EOF file for some acquisition. "
        " If --sentinel-file is specified instead, .EOF file will be downloaded",
    )
    parser.add_argument(
        "--orbit-save-dir",
        required=False,
        default="orbits/",
        help="Directory to save .EOF file into, or one that already contains "
        " .EOF files (default=%(default)s) ",
    )
    return parser.parse_args()


def _print_and_run(cmd):
    print(cmd)
    subprocess.run(cmd, shell=True, check=True)


# get the path of the script directory
CUR_PATH = os.path.dirname(os.path.abspath(sys.argv[0]))

if __name__ == "__main__":
    args = get_cli_args()
    if os.path.exists(args.outfile):
        print(f"{args.outfile} already exists. Exiting.")
        sys.exit(0)

    if not args.orbit_file:
        if not args.sentinel_file:
            print("No Sentinel-1 file specifiy. Searching current directory.")
            orbit_dir = args.orbit_save_dir
            eof.download.main(search_path=".", save_dir=orbit_dir)
            orbit_file = glob.glob(os.path.join(orbit_dir, "*.EOF"))[0]
    else:
        orbit_file = args.orbit_file
        
    if not args.sentinel_file:
        parsed_sentinel = list(eof.download.find_unique_safes("."))[0]
    else:
        parsed_sentinel = apertools.parsers.Sentinel(args.sentinel_file)
        
    start_time = parsed_sentinel.start_time
    min_time = start_time - timedelta(minutes=30)
    max_time = start_time + timedelta(minutes=30)
    orbit_tuples = eof.parsing.parse_orbit(orbit_file, min_time=min_time, max_time=max_time)

    orbtiming_name = "out.orbtiming"
    eof.parsing.write_orbinfo(orbit_tuples, outname=orbtiming_name)

    exe_file = f"{CUR_PATH}/build/create_los_map"
    cmd = f"{exe_file} {orbtiming_name} {args.dem}"

    _print_and_run(cmd)

    print("Saving .vrt files for new binary LOS files")
    for d in ("east", "north", "up"):
        # Create .vrt, copying the projection data from the .rsc file
        bin_name = f"los_{d}.bin"
        rsc_filename = f"{args.dem}.rsc"
        utils.save_as_vrt(bin_name, args.dem)

        # # Also make a smaller copy
        # cmd = f"gdal_translate -outsize 10% 10%  {bin_name}.vrt los_{d}_looked.tif"
        # _print_and_run(cmd)

    _print_and_run(f"gdal_merge.py -o {args.outfile} -separate los_*.vrt")
    # Clean up the intermediate LOS map files
    _print_and_run("rm -f los_*.bin los_*.bin.vrt")
