#!/usr/bin/env python3
"""
"""

import os
from pathlib import Path
import shutil
from unittest import TestCase
import logging
import json
from pprint import pprint

import flywheel_gear_toolkit
from flywheel_gear_toolkit.utils.zip_tools import unzip_archive

import run


def install_gear(zip_name):
    """unarchive initial gear to simulate running inside a real gear.

    This will delete and then install: config.json input/ output/ work/

    Args:
        zip_name (str): name of zip file that holds simulated gear.
    """

    gear_tests = "/src/tests/data/gear_tests/"
    gear = "/flywheel/v0/"
    os.chdir(gear)  # Make sure we're in the right place (gear works in "work/" dir)

    print("\nRemoving previous gear...")

    if Path(gear + "config.json").exists():
        Path(gear + "config.json").unlink()

    for dir_name in ["input", "output", "work"]:
        path = Path(gear + dir_name)
        if path.exists():
            shutil.rmtree(path)

    print(f'\ninstalling new gear, "{zip_name}"...')
    unzip_archive(gear_tests + zip_name, gear)

    # swap in user's api-key if there is one (fake) in the config
    config_json = Path("./config.json")
    if config_json.exists():
        print(f"Found {str(config_json)}")
        api_dict = None
        with open(config_json) as cjf:
            config_dict = json.load(cjf)
            # pprint(config_dict["inputs"])
            if "api_key" in config_dict["inputs"]:
                print(f'Found "api_key" in config_dict["inputs"]')

                user_json = Path(Path.home() / ".config/flywheel/user.json")
                if user_json.exists():
                    with open(user_json) as ujf:
                        api_dict = json.load(ujf)
                    config_dict["inputs"]["api_key"]["key"] = api_dict["key"]
                    print(f"installing api-key...")
                else:
                    print(f"{str(user_json)} not found.  Can't get api key.")
            else:
                print(f'No "api_key" in config_dict["inputs"]')

        if api_dict:
            with open(config_json, "w") as cjf:
                json.dump(config_dict, cjf)
    else:
        print(f"{str(config_json)} does not exist.  Can't set api key.")


def print_caplog(caplog):

    print("\nmessages")
    for ii, msg in enumerate(caplog.messages):
        print(f"{ii:2d} {msg}")
    print("\nrecords")
    for ii, rec in enumerate(caplog.records):
        print(f"{ii:2d} {rec}")


def search_caplog(caplog, find_me):
    """Search caplog message for find_me, return message"""

    for msg in caplog.messages:
        if find_me in msg:
            return msg
    return ""


def search_caplog_contains(caplog, find_me, contains_me):
    """Search caplog message for find_me, return true if it contains contins_me"""

    for msg in caplog.messages:
        if find_me in msg:
            print(f"Found '{find_me}' in '{msg}'")
            if contains_me in msg:
                print(f"Found '{contains_me}' in '{msg}'")
                return True
    return False


def print_captured(captured):

    print("\nout")
    for ii, msg in enumerate(captured.out.split("\n")):
        print(f"{ii:2d} {msg}")
    print("\nerr")
    for ii, msg in enumerate(captured.err.split("\n")):
        print(f"{ii:2d} {msg}")


#
#  Tests
#


def test_dry_run_works(caplog):

    user_json = Path(Path.home() / ".config/flywheel/user.json")
    if not user_json.exists():
        TestCase.skipTest("", f"No API key available in {str(user_json)}")

    caplog.set_level(logging.DEBUG)

    install_gear("dry_run.zip")

    with flywheel_gear_toolkit.GearToolkitContext(input_args=[]) as gtk_context:

        status = run.main(gtk_context)

        print_caplog(caplog)

        assert search_caplog(caplog, "Zipping work directory")
        assert search_caplog(caplog, "file:   ./bids/dataset_description.jso")
        assert search_caplog(caplog, "folder: ./reportlets/somecmd/sub-TOME3024/anat")
        assert search_caplog(
            caplog, "Could not find file 'anatsub-TOME3024_desc-about_T1w.html'"
        )
        assert search_caplog(caplog, "Warning: gear-dry-run is set")
        assert status == 0
