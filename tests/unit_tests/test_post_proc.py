import json
import logging
from pathlib import Path
from unittest import TestCase

import run

fs_dir = Path("/usr/local/freesurfer/")
subjects_dir = Path(fs_dir / "subjects")


log = logging.getLogger(__name__)


def test_convert_stats_works(caplog, install_gear, print_caplog):

    caplog.set_level(logging.DEBUG)

    install_gear("stats.zip")

    with open("/tmp/gear_environ.json", "r") as f:
        environ = json.load(f)

    run.do_gear_convert_stats("sub-TOME3024", False, environ, log)

    print_caplog(caplog)

    print(".metadat.json", json.dumps(run.METADATA, indent=4))

    assert Path("output/sub-TOME3024_rh_aparc_stats_area_mm2.csv").exists()
    assert (
        "Left-Lateral-Ventricle"
        in run.METADATA["analysis"]["info"]["aseg_stats_vol_mm3"]
    )
    assert (
        "lh_cuneus_area"
        in run.METADATA["analysis"]["info"]["lh_aparc.pial_stats_area_mm2"]
    )


def test_convert_volumes_works(caplog, install_gear, print_caplog):

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


def test_brainstem_works(caplog, install_gear, print_caplog):

    TestCase.skipTest("", f"Test takes too long.")

    caplog.set_level(logging.DEBUG)

    install_gear("hippo.zip")

    mri_dir = f"{str(subjects_dir)}/sub-TOME3024/mri"

    with open("/tmp/gear_environ.json", "r") as f:
        environ = json.load(f)

    run.do_gear_brainstem_structures("sub-TOME3024", mri_dir, False, environ, log)

    print_caplog(caplog)

    assert 0


def test_hippo_works(caplog, install_gear, print_caplog):

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
