#!/usr/bin/env python
import argparse
import glob
import os
import sys
import subprocess

# from orbitrangetime_lib import orbitrangetime
# from intp_orbit_lib import intp_orbit
# from llh2xyz import llh2xyz


def get_cli_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--outfile",
                        default="los_enu.tif",
                        help="Name of final, merged file with 3 bands "
                        "for east, north, and up LOS vectors "
                        "(default = %(default)s)")
    parser.add_argument("--orbit-file",
                        required=False,
                        help="Name of .orbtiming file for some acquisition")
    parser.add_argument("--dem", default="elevation.dem", 
                        help="Filepath of target DEM (default = %(default)s)")
    return parser.parse_args()


def _print_and_run(cmd):
    print(cmd)
    subprocess.run(cmd, shell=True, check=True)


# get the path of the script directory
CUR_PATH = os.path.dirname(os.path.abspath(sys.argv[0]))

if __name__ == "__main__":
    repo_home = os.path.expanduser("~/repos/sentinel_l0")
    args = get_cli_args()
    if os.path.exists(args.outfile):
        print(f"{args.outfile} already exists. Exiting.")
        sys.exit(0)

    if not args.orbit_file:
        orbit_file = glob.glob("*.orbtiming")[0]
    else:
        orbit_file = args.orbit_file


    cmd = f"{CUR_PATH}/create_los_map {orbit_file} {args.dem}"
    _print_and_run(cmd)

    print("Saving .vrt files for new binary LOS files")
    for d in ("east", "north", "up"):
        # Create .vrt, copying the projection data from the .rsc file
        bin_name = f"los_{d}.bin"
        rsc_filename = f"{args.dem}.rsc"
        cmd = f"aper save-vrt {bin_name} --rsc-file {rsc_filename} --dtype float32 --interleave BIP --num-bands 1"
        _print_and_run(cmd)

        # # Also make a smaller copy
        # cmd = f"gdal_translate -outsize 10% 10%  {bin_name}.vrt los_{d}_looked.tif"
        # _print_and_run(cmd)

    _print_and_run(f"gdal_merge.py -o {args.outfile} -separate los_*.vrt")
