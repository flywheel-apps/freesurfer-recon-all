#!/usr/bin/env python3
"""For test(s) *.zip, unzip into directory with same name.

Use "unpack-tests.py all" to unzip every test unless it is
already unzipped.

Example:
    unpack-tests.py hello_world.zip

"""

import argparse
import glob
import os
from pathlib import Path
from zipfile import ZipFile


def main():

    exit_code = 0

    # This can be run from:
    # - main repository directory
    # - tests/
    # - tests/bin/
    # - tests/data/
    # - tests/data/gear_tests/
    # Make sure running in proper place
    gear_test_paths = [
        "./tests/data/gear_tests",
        "./data/gear_tests",
        "../data/gear_tests",
        "./gear_tests",
    ]
    if Path.cwd().parts[-3:] == ("tests", "data", "gear_tests"):
        print(f"Unpacking tests in {str(Path.cwd())}")
    else:
        for gtp in gear_test_paths:
            if Path(gtp).exists():
                print(f"Unpacking tests in {str(Path(gtp))}")
                os.chdir(Path(gtp))

    if args.test == "all":
        tests = glob.glob("*.zip")
    else:
        tests = [args.test]

    for test in tests:

        name = test[:-4]
        if args.verbose > 0:
            print(f'"{test}" --> "{name}"')

        if Path(name).exists():
            print(f"{name} already exsts, not unzipping.")
        else:
            print(f"Unzipping {name}.")
            zip_file = ZipFile(test, "r")
            zip_file.extractall(name)

    return exit_code


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("test", help="The name of a test .zip file.")
    parser.add_argument("-v", "--verbose", action="count", default=0)

    args = parser.parse_args()

    os.sys.exit(main())
