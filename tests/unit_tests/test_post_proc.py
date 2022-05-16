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

    metadata = {"analysis": {"info": {}}}

    run.do_gear_convert_stats("sub-TOME3024", False, environ, metadata)

    print_caplog(caplog)

    print(".metadat.json", json.dumps(metadata, indent=4))

    assert Path("output/sub-TOME3024_rh_aparc_stats_area_mm2.csv").exists()
    assert (
        "Left-Lateral-Ventricle" in metadata["analysis"]["info"]["aseg_stats_vol_mm3"]
    )
    assert (
        "lh_cuneus_area" in metadata["analysis"]["info"]["lh_aparc.pial_stats_area_mm2"]
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
    run.do_gear_convert_volumes(config, mri_dir, False, environ)

    print_caplog(caplog)

    assert Path("output/brainstemSsLabels.v12.FSvoxelSpace.nii.gz").exists()


def test_brainstem_works(caplog, install_gear, print_caplog):

    TestCase.skipTest("", f"Test takes too long.")

    caplog.set_level(logging.DEBUG)

    install_gear("hippo.zip")

    mri_dir = f"{str(subjects_dir)}/sub-TOME3024/mri"

    metadata = {"analysis": {"info": {}}}

    with open("/tmp/gear_environ.json", "r") as f:
        environ = json.load(f)

    run.do_gear_brainstem_structures(
        "sub-TOME3024", mri_dir, False, environ, metadata
    )

    print_caplog(caplog)

    assert 0


def test_hippo_works(caplog, install_gear, print_caplog):

    TestCase.skipTest("", f"Test takes too long.")

    caplog.set_level(logging.DEBUG)

    install_gear("hippo.zip")

    metadata = {"analysis": {"info": {}}}

    mri_dir = f"{str(subjects_dir)}/sub-TOME3024/mri"

    with open("/tmp/gear_environ.json", "r") as f:
        environ = json.load(f)

    # This takes 20 minutes!
    run.do_gear_hippocampal_subfields(
        "sub-TOME3024", mri_dir, False, environ, metadata
    )

    print_caplog(caplog)

    assert 0


def test_gtmseg_dry_run_works(caplog, search_caplog, print_caplog):

    caplog.set_level(logging.DEBUG)

    with open("/tmp/gear_environ.json", "r") as f:
        environ = json.load(f)

    run.do_gtmseg("sub-TOME3024", True, environ)

    print_caplog(caplog)

    assert search_caplog(caplog, "gtmseg --s sub-TOME3024")


def test_do_gear_thalamic_nuclei_dry_run_works(
    caplog, install_gear, search_caplog, print_caplog
):

    caplog.set_level(logging.DEBUG)

    install_gear("thalamic.zip")

    with open("/tmp/gear_environ.json", "r") as f:
        environ = json.load(f)

    metadata = {"analysis": {"info": {}}}

    mri_dir = f"{str(subjects_dir)}/sub-TOME3024/mri"

    run.do_gear_thalamic_nuclei("sub-TOME3024", mri_dir, True, environ, metadata)

    print(".metadat.json", json.dumps(metadata, indent=4))
    print_caplog(caplog)

    assert search_caplog(caplog, "segmentThalamicNuclei.sh sub-TOME3024")
    assert (
        metadata["analysis"]["info"]["ThalamicNuclei.v12.T1.volumes"][
            "Right-Whole_thalamus"
        ]
        == 7476.300538
    )
