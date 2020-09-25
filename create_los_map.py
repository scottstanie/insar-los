#!/usr/bin/env python
import argparse
import os
import sys
import subprocess

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
    parser.add_argument(
        "--orbtiming-file",
        required=False,
        default="out.orbtiming",
        help="File contining parsed OSVs in format `t x y z vx vy vz ax ay az` "
        " , will be created if none exists. (default=%(default)s) ",
    )

    return parser.parse_args()


def _print_and_run(cmd):
    print(cmd)
    subprocess.run(cmd, shell=True, check=True)


# get the path of the script directory
CUR_PATH = os.path.dirname(os.path.abspath(sys.argv[0]))


def main():
    args = get_cli_args()
    if os.path.exists(args.outfile):
        print(f"{args.outfile} already exists. Exiting.")
        sys.exit(0)

    if not os.path.exists(args.orbtiming_file):
        print(f"{args.orbtiming_file} does not exist. Creating.")
        utils.create_orbtiming_file(args)

    exe_file = f"{CUR_PATH}/build/create_los_map"
    cmd = f"{exe_file} {args.orbtiming_file} {args.dem}"

    _print_and_run(cmd)

    print("Saving .vrt files for new binary LOS files")
    for d in ("east", "north", "up"):
        # Create .vrt, copying the projection data from the DEM
        bin_name = f"los_{d}.bin"
        utils.save_as_vrt(bin_name, args.dem)

        # # Also make a smaller copy
        # cmd = f"gdal_translate -outsize 10% 10%  {bin_name}.vrt los_{d}_looked.tif"
        # _print_and_run(cmd)

    _print_and_run(f"gdal_merge.py -o {args.outfile} -separate los_*.vrt")
    # Clean up the intermediate LOS map files
    _print_and_run("rm -f los_*.bin los_*.bin.vrt")


if __name__ == "__main__":
    main()
