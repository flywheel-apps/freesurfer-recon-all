#! /usr/bin/env python3
#
# Given a Flywheel job id, this script will generate a local testing directory
# within which you can run the job locally, using Docker, as it ran in Flywheel.
#
# This code generates a directory structure that mimics exactly what the Gear would
# get when running in Flywheel. Importantly, this code will generate a "config.json"
# file, which contains all of the metadata the Gear received when running in Flywheel.
#
#  For a given job this script will:
#         1. Make directory structure (gear_job base dir, inputs, outputs)
#         2. Write a valid config.json file
#         3. Download required data to inputs directories
#
# Usage:
#   Positional inputs:
#       [1] - Job ID
#       [2] - (Optional) Directory to save job contents. Defaults to cwd.
#
#   fwutil_job_run_local.py <job_id> <output_base_directory>
#
# Example:
#   fwutil_job_run_local.py 298e73lacbde98273lkad
#
#


import json
import os
import sys

import flywheel_gear_toolkit


def build_local_test(job, test_path_root):
    """
    Build a local testing instance for a given Flywheel job
    """

    # Make directories
    test_path = os.path.join(
        test_path_root, job.gear_info.name + "-" + job.gear_info.version + "_" + job.id
    )
    input_dir = os.path.join(test_path, "input")
    output_dir = os.path.join(test_path, "output")

    if not os.path.isdir(input_dir):
        print("Creating directory: %s" % input_dir)
        os.makedirs(input_dir)

    if not os.path.isdir(output_dir):
        print("Creating directory: %s" % output_dir)
        os.mkdir(output_dir)

    # Write the config file
    config_file = os.path.join(test_path, "config.json")
    with open(config_file, "w") as cf:
        json.dump(job["config"], cf, indent=4)

    # For each key in input, make the directory and download the data
    input_data = job.config.get("inputs")

    for k in input_data:

        if k == "api_key":
            continue

        _input = input_data[k]

        # Make the directory
        ipath = os.path.join(input_dir, k)
        if os.path.exists(ipath):
            print("Exists: %s" % ipath)
        else:
            os.mkdir(ipath)
            print("Created directory: %s" % ipath)

        # Download the file to the directory
        ifilename = _input["location"]["name"]
        ifilepath = os.path.join(ipath, ifilename)
        iparentid = _input["hierarchy"]["id"]

        if os.path.isfile(ifilepath):
            print("Exists: %s" % ifilename)
        else:
            print("Downloading: %s" % ifilename)
            fw.download_file_from_container(iparentid, ifilename, ifilepath)

    print("Done!")


if __name__ == "__main__":
    """
    Given a Flywheel job id, this script will generate a local testing directory
    within which you can run the job locally, using Docker, as it ran in Flywheel.
    Positional inputs:
        [1] - Job ID
        [2] - (Optional) Directory to save job contents. Defaults to cwd.
    """

    if not sys.argv[1]:
        raise ValueError("API KEY required")
    else:
        job_id = sys.argv[1]

    gtk_context = flywheel_gear_toolkit.GearToolkitContext()
    fw = gtk_context.client

    # Get the job
    job = fw.get_job(job_id)

    # Build the local test
    if len(sys.argv) == 3:
        test_path_root = sys.argv[2]
    else:
        test_path_root = os.getcwd()

    build_local_test(job, test_path_root)
