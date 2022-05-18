"""Unit tests for generate_command"""

import logging
from pathlib import Path

from run import generate_command

log = logging.getLogger(__name__)


def test_generate_command_works(capsys):

    # create required input file
    anatomical = Path("/flywheel/v0/input/anatomical")
    if not anatomical.exists():
        anatomical.mkdir(parents=True)
    (anatomical / "nifty.nii.gz").touch(exist_ok=True)

    subject_id = "That's Mr. Subject to you Pal!"

    command_config = {
        "parallel": True,
        "reconall_options": "-all -qcache",
        "openmp": 11,
        "expert": "/flywheel/v0/input/expert/expert.opts",
    }


    command = generate_command(subject_id, command_config)

    print(command)

    assert command[1] == "recon-all"
    assert command[5] == subject_id
    assert command[-2] == "-expert"
