#!/usr/bin/env python3
"""
"""

import json
import logging
import os
import shutil
from pathlib import Path
from unittest import TestCase

import flywheel_gear_toolkit
import pytest
from flywheel_gear_toolkit.utils.zip_tools import unzip_archive

import run

log = logging.getLogger(__name__)

fs_dir = Path("/usr/local/freesurfer/")
subjects_dir = Path(fs_dir / "subjects")


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

    for dir_name in ["input", "output", "work", "freesurfer"]:
        path = Path(gear + dir_name)
        if path.exists():
            shutil.rmtree(path)

    print(f'\ninstalling new gear, "{zip_name}"...')
    unzip_archive(gear_tests + zip_name, gear)

    # move freesurfer license and subject directories to proper place
    gear_freesurfer = Path("freesurfer")
    if gear_freesurfer.exists():
        gear_license = Path(gear_freesurfer / "license.txt")
        if gear_license.exists():
            if Path(fs_dir / "license.txt").exists():
                Path(fs_dir / "license.txt").unlink()
            shutil.move(str(gear_license), str(fs_dir))
        subjects = gear_freesurfer.glob("subjects/*")
        for subj in subjects:
            subj_name = subj.name
            if (subjects_dir / subj_name).exists():
                shutil.rmtree(subjects_dir / subj_name)
            print(f"moving subject to {str(subjects_dir / subj_name)}")
            shutil.move(str(subj), str(subjects_dir))


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
    """Search caplog message for find_me, return true if it contains contains_me"""

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

ANATOMICAL_STR = "anatomical is '/flywheel/v0/input/anatomical/dicoms/1.2.826.0.1.3680043.8.498.81096423295716363709677774784503056177.MR.dcm'"


def test_convert_stats_works(caplog):

    caplog.set_level(logging.DEBUG)

    install_gear("stats.zip")

    with open("/tmp/gear_environ.json", "r") as f:
        environ = json.load(f)

    run.do_gear_convert_stats("sub-TOME3024", False, environ, log)

    print_caplog(caplog)

    assert Path("output/sub-TOME3024_rh_aparc_stats_area_mm2.csv").exists()


def test_convert_volumes_works(caplog):

    caplog.set_level(logging.DEBUG)

    install_gear("convert.zip")

    mri_dir = f"{str(subjects_dir)}/sub-TOME3024/mri"

    with open("/tmp/gear_environ.json", "r") as f:
        environ = json.load(f)

    config = {
        "gear-hippocampal_subfields": True,
        "gear-brainstem_structures": True,
    }
    run.do_gear_convert_volumes(config, mri_dir, False, environ, log)

    print_caplog(caplog)

    assert Path("output/brainstemSsLabels.v12.FSvoxelSpace.nii.gz").exists()


def test_brainstem_works(caplog):

    TestCase.skipTest("", f"Test takes too long.")

    caplog.set_level(logging.DEBUG)

    install_gear("hippo.zip")

    mri_dir = f"{str(subjects_dir)}/sub-TOME3024/mri"

    with open("/tmp/gear_environ.json", "r") as f:
        environ = json.load(f)

    run.do_gear_brainstem_structures("sub-TOME3024", mri_dir, False, environ, log)

    print_caplog(caplog)

    assert 0


def test_hippo_works(caplog):

    TestCase.skipTest("", f"Test takes too long.")

    caplog.set_level(logging.DEBUG)

    install_gear("hippo.zip")

    mri_dir = f"{str(subjects_dir)}/sub-TOME3024/mri"

    with open("/tmp/gear_environ.json", "r") as f:
        environ = json.load(f)

    # This takes 20 minutes!
    run.do_gear_hippocampal_subfields("sub-TOME3024", mri_dir, False, environ, log)

    print_caplog(caplog)

    assert 0


def test_dry_run_works(caplog):

    user_json = Path(Path.home() / ".config/flywheel/user.json")
    if not user_json.exists():
        TestCase.skipTest("", f"No API key available in {str(user_json)}")

    caplog.set_level(logging.DEBUG)

    install_gear("dry_run.zip")

    with flywheel_gear_toolkit.GearToolkitContext(input_args=[]) as gtk_context:

        with pytest.raises(SystemExit) as excinfo:

            run.main(gtk_context)

        print_caplog(caplog)
        print(excinfo)

        assert excinfo.type == SystemExit
        assert excinfo.value.code == 0
        assert search_caplog(caplog, "Warning: gear-dry-run is set")


def test_prev_works(caplog):

    user_json = Path(Path.home() / ".config/flywheel/user.json")
    if not user_json.exists():
        TestCase.skipTest("", f"No API key available in {str(user_json)}")

    caplog.set_level(logging.DEBUG)

    install_gear("prev.zip")

    with flywheel_gear_toolkit.GearToolkitContext(input_args=[]) as gtk_context:

        with pytest.raises(SystemExit) as excinfo:

            run.main(gtk_context)

        print_caplog(caplog)
        print(excinfo)

        assert excinfo.type == SystemExit
        assert excinfo.value.code == 0
        assert search_caplog(caplog, "Warning: gear-dry-run is set")
        command = search_caplog(caplog, "command is:")
        assert command[34:56] == "'-subjid', 'TOME_3024'"


def test_nii2_works(caplog):

    user_json = Path(Path.home() / ".config/flywheel/user.json")
    if not user_json.exists():
        TestCase.skipTest("", f"No API key available in {str(user_json)}")

    caplog.set_level(logging.DEBUG)

    install_gear("nii2.zip")

    with flywheel_gear_toolkit.GearToolkitContext(input_args=[]) as gtk_context:

        with pytest.raises(SystemExit) as excinfo:

            run.main(gtk_context)

        print_caplog(caplog)
        print(excinfo)

        assert excinfo.type == SystemExit
        assert excinfo.value.code == 0
        assert search_caplog(caplog, "Warning: gear-dry-run is set")
        command = search_caplog(caplog, "command is:")
        assert command[34:86] == "'-i', '/flywheel/v0/input/anatomical/T1w_MPR.nii.gz'"
        assert (
            command[89:146]
            == "-i', '/flywheel/v0/input/t1w_anatomical_2/T1w_MPR.nii.gz'"
        )
        assert "-openmp" in command


def test_dcm_zip_works(caplog):

    user_json = Path(Path.home() / ".config/flywheel/user.json")
    if not user_json.exists():
        TestCase.skipTest("", f"No API key available in {str(user_json)}")

    caplog.set_level(logging.DEBUG)

    install_gear("dcm_zip.zip")

    with flywheel_gear_toolkit.GearToolkitContext(input_args=[]) as gtk_context:

        with pytest.raises(SystemExit) as excinfo:

            run.main(gtk_context)

        print_caplog(caplog)
        print(excinfo)

        assert excinfo.type == SystemExit
        assert excinfo.value.code == 0
        assert search_caplog(caplog, ANATOMICAL_STR)
        assert search_caplog(caplog, "Warning: gear-dry-run is set")
        command = search_caplog(caplog, "command is:")
        assert (
            command[12:78]
            == "['time', 'recon-all', '-i', '/flywheel/v0/input/anatomical/dicoms/"
        )
        assert "-openmp" in command


def test_wet_run_fails(caplog):

    # clean up after previous tests so this one will run
    shutil.rmtree("/usr/local/freesurfer/subjects/TOME_3024")

    user_json = Path(Path.home() / ".config/flywheel/user.json")
    if not user_json.exists():
        TestCase.skipTest("", f"No API key available in {str(user_json)}")

    caplog.set_level(logging.DEBUG)

    install_gear("wet_run.zip")

    with flywheel_gear_toolkit.GearToolkitContext(input_args=[]) as gtk_context:

        with pytest.raises(SystemExit) as excinfo:

            run.main(gtk_context)

        print_caplog(caplog)
        print(excinfo)

        assert excinfo.type == SystemExit
        assert excinfo.value.code == 1
        # Make sure it saves output even after an error
        assert search_caplog(
            caplog,
            "Zipping output file freesurfer-recon-all_TOME_3024_5db3392669d4f3002a16ec4c.zip",
        )
        # Make sure subject was kept
        assert Path("/flywheel/v0/output/TOME_3024/scripts/recon-all.error").exists()