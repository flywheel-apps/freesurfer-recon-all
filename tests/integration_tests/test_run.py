#!/usr/bin/env python3
"""Test in a gear-like environment by unzipping config.json, input/, output, etc."""

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


ANATOMICAL_STR = "anatomical is '/flywheel/v0/input/anatomical/dicoms/1.2.826.0.1.3680043.8.498.81096423295716363709677774784503056177.MR.dcm'"


def test_dry_run_works(capfd, install_gear, print_captured, search_sysout):

    user_json = Path(Path.home() / ".config/flywheel/user.json")
    if not user_json.exists():
        TestCase.skipTest("", f"No API key available in {str(user_json)}")

    install_gear("dry_run.zip")

    with flywheel_gear_toolkit.GearToolkitContext(input_args=[]) as gtk_context:

        with pytest.raises(SystemExit) as excinfo:

            run.main(gtk_context)

        captured = capfd.readouterr()
        print_captured(captured)

        # print("run.METADATA", json.dumps(run.METADATA, indent=4))

        with open("/flywheel/v0/output/.metadata.json", "r") as fff:
            metadata = json.load(fff)

        assert excinfo.type == SystemExit
        assert excinfo.value.code == 0
        assert search_sysout(captured, "Warning: gear-dry-run is set")
        assert search_sysout(captured, "Gear succeeded on first try!")
        assert "How dry I am" in metadata["analysis"]["info"]["dry_run"]
        assert (
            "Whole_hippocampus"
            in metadata["analysis"]["info"]["rh.hippoSfVolumes-T1.v21"]
        )
        assert (
            "Basal-nucleus" in metadata["analysis"]["info"]["lh.amygNucVolumes-T1.v21"]
        )
        assert "Midbrain" in metadata["analysis"]["info"]["brainstemSsVolumes.v2"]
        assert 0


def test_prev_works(capfd, install_gear, print_captured, search_sysout):

    user_json = Path(Path.home() / ".config/flywheel/user.json")
    if not user_json.exists():
        TestCase.skipTest("", f"No API key available in {str(user_json)}")

    install_gear("prev.zip")

    with flywheel_gear_toolkit.GearToolkitContext(input_args=[]) as gtk_context:

        with pytest.raises(SystemExit) as excinfo:

            run.main(gtk_context)

        captured = capfd.readouterr()
        print_captured(captured)

        assert excinfo.type == SystemExit
        assert excinfo.value.code == 0
        assert search_sysout(captured, "Warning: gear-dry-run is set")
        command = search_sysout(captured, "running from previous run")
        assert "-subjid TOME_3024" in command


def test_nii2_works(capfd, install_gear, print_captured, search_sysout):

    user_json = Path(Path.home() / ".config/flywheel/user.json")
    if not user_json.exists():
        TestCase.skipTest("", f"No API key available in {str(user_json)}")

    install_gear("nii2.zip")

    with flywheel_gear_toolkit.GearToolkitContext(input_args=[]) as gtk_context:

        with pytest.raises(SystemExit) as excinfo:

            run.main(gtk_context)

        captured = capfd.readouterr()
        print_captured(captured)

        assert excinfo.type == SystemExit
        assert excinfo.value.code == 0
        assert search_sysout(captured, "Warning: gear-dry-run is set")
        command = search_sysout(captured, "command is:")
        assert "'-i', '/flywheel/v0/input/anatomical/T1w_MPR.nii.gz'" in command
        assert "-i', '/flywheel/v0/input/t1w_anatomical_2/T1w_MPR.nii.gz'" in command
        assert "-openmp" in command


def test_dcm_zip_works(capfd, search_sysout, install_gear, print_captured):

    user_json = Path(Path.home() / ".config/flywheel/user.json")
    if not user_json.exists():
        TestCase.skipTest("", f"No API key available in {str(user_json)}")

    install_gear("dcm_zip.zip")

    with flywheel_gear_toolkit.GearToolkitContext(input_args=[]) as gtk_context:

        with pytest.raises(SystemExit) as excinfo:

            run.main(gtk_context)

        captured = capfd.readouterr()
        print_captured(captured)

        assert excinfo.type == SystemExit
        assert excinfo.value.code == 0
        assert search_sysout(captured, ANATOMICAL_STR)
        assert search_sysout(captured, "Warning: gear-dry-run is set")
        command = search_sysout(captured, "command is:")
        assert (
            "['time', 'recon-all', '-i', '/flywheel/v0/input/anatomical/dicoms/"
            in command
        )
        assert "-openmp" in command


def test_wet_run_fails(capfd, search_sysout, install_gear, print_captured):

    # clean up after previous tests so this one will run
    shutil.rmtree("/usr/local/freesurfer/subjects/TOME_3024")

    user_json = Path(Path.home() / ".config/flywheel/user.json")
    if not user_json.exists():
        TestCase.skipTest("", f"No API key available in {str(user_json)}")

    install_gear("wet_run.zip")

    with flywheel_gear_toolkit.GearToolkitContext(input_args=[]) as gtk_context:

        with pytest.raises(SystemExit) as excinfo:

            run.main(gtk_context)

        captured = capfd.readouterr()
        print_captured(captured)

        assert excinfo.type == SystemExit
        assert excinfo.value.code == 1
        # Make sure it saves output even after an error
        assert search_sysout(
            captured,
            "Zipping output file freesurfer-recon-all_TOME_3024_5db3392669d4f3002a16ec4c.zip",
        )
        assert search_sysout(captured, "Gear failed on second attempt")
        assert search_sysout(captured, "time recon-all -subjid TOME_3024 -all")
