#!/usr/bin/env python3
"""For directory/ies in the current directory zip into a test
.zip archive with same name.

This will REMOVE the test .zip file if it already exists and it
will remove the test directory after zipping.

Use "pack-tests.py all" to zip every test unless it is already
unzipped.

Example:
    pack-tests.py hello_world

"""

import argparse
import glob
import os
import shutil
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


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
        print(f"Packing tests in {str(Path.cwd())}")
    else:
        for gtp in gear_test_paths:
            if Path(gtp).exists():
                print(f"Packing tests in {str(Path(gtp))}")
                os.chdir(Path(gtp))

    if args.test == "all":
        tests = glob.glob("*")
        if args.verbose > 0:
            print(tests)
    else:
        tests = [args.test]

    for test in tests:

        if test[-1] == "/":
            test = test[:-1]

        if Path(test).is_dir():

            name = test + ".zip"
            if args.verbose > 0:
                print(f'"{test}" --> "{name}"')

            if Path(name).exists():
                print(f"Deleting {name}")
                Path(name).unlink()

            print(f"Creating {name}")
            with ZipFile(name, "w", ZIP_DEFLATED) as outzip:
                os.chdir(test)
                for root, subdirs, files in os.walk("."):
                    for fl in files + subdirs:
                        fl_path = Path(root) / fl
                        if args.verbose > 0:
                            print(f"adding {fl_path}")
                        outzip.write(fl_path)
                os.chdir("..")

            print(f"Removing {test}")
            shutil.rmtree(test)

        else:
            if Path(test).exists():
                print(f"Ignoring {test}")

    return exit_code


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("test", help="The name of a test .zip file.")
    parser.add_argument("-v", "--verbose", action="count", default=0)

    args = parser.parse_args()

    os.sys.exit(main())
