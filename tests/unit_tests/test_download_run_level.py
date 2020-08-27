"""Unit tests for download_run_level.py"""

import copy
import json
import logging
from pathlib import Path
from unittest.mock import patch

import flywheel
import flywheel_gear_toolkit

from utils.bids.download_run_level import (
    download_bids_for_runlevel,
    fix_dataset_description,
)
from utils.bids.errors import BIDSExportError

DATASET_DESCRIPTION = {
    "Acknowledgements": "",
    "Authors": [],
    "BIDSVersion": "1.2.0",
    "DatasetDOI": "",
    "Funding": [],
    "HowToAcknowledge": "",
    "License": "",
    "Name": "tome",
    "ReferencesAndLinks": [],
    "template": "project",
}


def test_fix_dataset_description_reports_good(tmp_path, caplog):
    """Make sure a proper file is logged as being so."""

    caplog.set_level(logging.DEBUG)

    bids_path = tmp_path
    with open(Path(bids_path) / "dataset_description.json", "w") as jfp:
        json.dump(DATASET_DESCRIPTION, jfp)

    fix_dataset_description(bids_path)

    assert len(caplog.records) == 1
    assert "Funding is: <class 'list'>" in caplog.records[0].message


def test_fix_dataset_description_fixes(tmp_path, caplog):
    """Make sure the Funding is changed to be a list."""

    caplog.set_level(logging.DEBUG)

    # mess and fool around like the bids_client used to
    DATASET_DESCRIPTION["Funding"] = ""

    bids_path = tmp_path
    with open(Path(bids_path) / "dataset_description.json", "w") as jfp:
        json.dump(DATASET_DESCRIPTION, jfp)

    fix_dataset_description(bids_path)

    with open(Path(bids_path) / "dataset_description.json", "r") as jfp:
        fixed_json = json.load(jfp)

    assert len(caplog.records) == 3
    assert "is not a list" in caplog.records[1].message

    DATASET_DESCRIPTION["Funding"] = []
    assert fixed_json == DATASET_DESCRIPTION


def test_fix_dataset_description_missing_creates(tmp_path, caplog):

    caplog.set_level(logging.DEBUG)

    bids_path = tmp_path

    fix_dataset_description(bids_path)

    with open(Path(bids_path) / "dataset_description.json", "r") as jfp:
        fixed_json = json.load(jfp)

    assert fixed_json == DATASET_DESCRIPTION

    assert len(caplog.records) == 1
    assert "Creating default dataset_description.json file" in caplog.records[0].message


HIERARCHY = {
    "run_level": "acquisition",
    "run_label": "acquisition_label",
    "group": "monkeyshine",
    "project_label": "TheProjectLabel",
    "subject_label": "TheSubjectCode",
    "session_label": "TheSessionLabel",
    "acquisition_label": "TheAcquisitionLabel",
}


class Acquisition:
    def __init__(self):
        self.label = "TheAcquisitionLabel"


def test_download_bids_for_runlevel_acquisition_works(tmp_path, caplog):

    caplog.set_level(logging.DEBUG)

    with patch(
        "flywheel_gear_toolkit.GearToolkitContext.client", return_value=Acquisition(),
    ):

        with patch("utils.bids.download_run_level.download_bids_dir"):

            with patch(
                "utils.bids.download_run_level.validate_bids", return_value=0,
            ):

                gtk_context = flywheel_gear_toolkit.GearToolkitContext(
                    input_args=[], gear_path=tmp_path
                )

                # create expected file
                bids_path = Path(gtk_context.work_dir) / "bids"
                bids_path.mkdir()
                with open(bids_path / "dataset_description.json", "w") as jfp:
                    json.dump(DATASET_DESCRIPTION, jfp)

                err_code = download_bids_for_runlevel(
                    gtk_context,
                    HIERARCHY,
                    tree=False,
                    tree_title=None,
                    src_data=False,
                    folders=[],
                    dry_run=False,
                )

    assert len(caplog.records) == 9
    assert "Downloading BIDS data was successful" in caplog.records[8].message


def test_download_bids_for_runlevel_no_destination_complains(tmp_path, caplog):

    caplog.set_level(logging.DEBUG)

    HIERARCHY["run_level"] = "no_destination"

    with patch(
        "flywheel_gear_toolkit.GearToolkitContext.client", return_value=Acquisition(),
    ):

        with patch("utils.bids.download_run_level.download_bids_dir"):

            with patch(
                "utils.bids.download_run_level.validate_bids", return_value=0,
            ):

                gtk_context = flywheel_gear_toolkit.GearToolkitContext(
                    input_args=[], gear_path=tmp_path
                )

                err_code = download_bids_for_runlevel(
                    gtk_context,
                    HIERARCHY,
                    tree=False,
                    tree_title=None,
                    src_data=True,
                    folders=[],
                    dry_run=True,
                )

    assert len(caplog.records) == 2
    assert "Destination does not exist" in caplog.records[0].message

    HIERARCHY["run_level"] = "acquisition"  # fix what was broke


def test_download_bids_for_runlevel_project_works(tmp_path, caplog):

    caplog.set_level(logging.DEBUG)

    HIERARCHY["run_level"] = "project"

    # create expected file
    bids_path = Path(tmp_path) / "work/bids"
    bids_path.mkdir(parents=True)
    with open(bids_path / "dataset_description.json", "w") as jfp:
        json.dump(DATASET_DESCRIPTION, jfp)

    with patch(
        "flywheel_gear_toolkit.GearToolkitContext.client", return_value=Acquisition(),
    ):

        with patch(
            "flywheel_gear_toolkit.GearToolkitContext.download_project_bids",
            return_value=bids_path,
        ):

            with patch(
                "utils.bids.download_run_level.validate_bids", return_value=0,
            ):

                gtk_context = flywheel_gear_toolkit.GearToolkitContext(
                    input_args=["-d aex:analysis"], gear_path=tmp_path
                )

                err_code = download_bids_for_runlevel(
                    gtk_context,
                    HIERARCHY,
                    tree=True,
                    tree_title=None,
                    src_data=True,
                    folders=[],
                    dry_run=True,
                )

    assert len(caplog.records) == 10
    assert 'project "TheProjectLabel"' in caplog.records[3].message
    assert 'Getting "tree" listing' in caplog.records[8].message

    HIERARCHY["run_level"] = "acquisition"  # fix what was broke


def test_download_bids_for_runlevel_bad_destination_noted(tmp_path, caplog):

    caplog.set_level(logging.DEBUG)

    HIERARCHY["run_level"] = "subject"

    # create expected file
    bids_path = Path(tmp_path) / "work/bids"
    bids_path.mkdir(parents=True)
    with open(bids_path / "dataset_description.json", "w") as jfp:
        json.dump(DATASET_DESCRIPTION, jfp)

    with patch(
        "flywheel_gear_toolkit.GearToolkitContext.client", return_value=Acquisition(),
    ):

        with patch(
            "flywheel_gear_toolkit.GearToolkitContext.download_project_bids",
            return_value=bids_path,
        ):

            with patch(
                "utils.bids.download_run_level.validate_bids", return_value=0,
            ):

                gtk_context = flywheel_gear_toolkit.GearToolkitContext(
                    input_args=["-d aex:bad_destination"], gear_path=tmp_path
                )

                err_code = download_bids_for_runlevel(
                    gtk_context,
                    HIERARCHY,
                    tree=False,
                    tree_title=None,
                    src_data=True,
                    folders=[" anat", "func"],
                    dry_run=True,
                )

    assert len(caplog.records) == 9
    assert "is not an analysis or acquisition" in caplog.records[0].message
    assert 'subject "TheSubjectCode"' in caplog.records[4].message

    HIERARCHY["run_level"] = "acquisition"  # fix what was broke


def test_download_bids_for_runlevel_unknown_acqusition_detected(tmp_path, caplog):

    caplog.set_level(logging.DEBUG)

    hierarchy = copy.deepcopy(HIERARCHY)
    hierarchy["acquisition_label"] = "unknown acqusition"

    # create expected file
    bids_path = Path(tmp_path) / "work/bids"
    bids_path.mkdir(parents=True)
    with open(bids_path / "dataset_description.json", "w") as jfp:
        json.dump(DATASET_DESCRIPTION, jfp)

    with patch(
        "flywheel_gear_toolkit.GearToolkitContext.client", return_value=Acquisition(),
    ):

        with patch(
            "flywheel_gear_toolkit.GearToolkitContext.download_project_bids",
            return_value=bids_path,
        ):

            with patch(
                "utils.bids.download_run_level.validate_bids", return_value=0,
            ):

                gtk_context = flywheel_gear_toolkit.GearToolkitContext(
                    input_args=["-d aex:analysis"], gear_path=tmp_path
                )

                err_code = download_bids_for_runlevel(
                    gtk_context,
                    hierarchy,
                    tree=False,
                    tree_title=None,
                    src_data=True,
                    folders=["anat", "func"],
                    dry_run=True,
                )

    assert len(caplog.records) == 5
    assert 'acquisition "unknown acqusition"' in caplog.records[3].message


def test_download_bids_for_runlevel_session_works(tmp_path, caplog):

    caplog.set_level(logging.DEBUG)

    HIERARCHY["run_level"] = "session"

    # create expected file
    bids_path = Path(tmp_path) / "work/bids"
    bids_path.mkdir(parents=True)
    with open(bids_path / "dataset_description.json", "w") as jfp:
        json.dump(DATASET_DESCRIPTION, jfp)

    with patch(
        "flywheel_gear_toolkit.GearToolkitContext.client", return_value=Acquisition(),
    ):

        with patch(
            "flywheel_gear_toolkit.GearToolkitContext.download_project_bids",
            return_value=bids_path,
        ):

            with patch(
                "utils.bids.download_run_level.validate_bids", return_value=0,
            ):

                gtk_context = flywheel_gear_toolkit.GearToolkitContext(
                    input_args=["-d aex:analysis"], gear_path=tmp_path
                )

                err_code = download_bids_for_runlevel(
                    gtk_context,
                    HIERARCHY,
                    tree=False,
                    tree_title=None,
                    src_data=True,
                    folders=["anat", "func"],
                    dry_run=True,
                )

    assert len(caplog.records) == 8
    assert 'session "TheSessionLabel"' in caplog.records[3].message

    HIERARCHY["run_level"] = "acquisition"  # fix what was broke


def test_download_bids_for_runlevel_acquisition_exception_detected(tmp_path, caplog):

    caplog.set_level(logging.DEBUG)

    with patch(
        "flywheel_gear_toolkit.GearToolkitContext.client", return_value=Acquisition(),
    ):

        with patch(
            "utils.bids.download_run_level.download_bids_dir",
            side_effect=flywheel.ApiException("foo", "fum"),
        ):

            with patch(
                "utils.bids.download_run_level.validate_bids", return_value=0,
            ):

                gtk_context = flywheel_gear_toolkit.GearToolkitContext(
                    input_args=["-d aex:analysis"], gear_path=tmp_path
                )

                err_code = download_bids_for_runlevel(
                    gtk_context,
                    HIERARCHY,
                    tree=False,
                    tree_title=None,
                    src_data=True,
                    folders=["anat", "func"],
                    dry_run=True,
                )

    assert len(caplog.records) == 6
    assert "(foo) Reason: fum" in caplog.records[4].message


def test_download_bids_for_runlevel_unknown_detected(tmp_path, caplog):

    caplog.set_level(logging.DEBUG)

    HIERARCHY["run_level"] = "who knows"

    # create expected file
    bids_path = Path(tmp_path) / "work/bids"
    bids_path.mkdir(parents=True)
    with open(bids_path / "dataset_description.json", "w") as jfp:
        json.dump(DATASET_DESCRIPTION, jfp)

    with patch(
        "flywheel_gear_toolkit.GearToolkitContext.client", return_value=Acquisition(),
    ):

        with patch(
            "utils.bids.download_run_level.validate_bids", return_value=0,
        ):

            gtk_context = flywheel_gear_toolkit.GearToolkitContext(
                input_args=["-d aex:analysis"], gear_path=tmp_path
            )

            err_code = download_bids_for_runlevel(
                gtk_context,
                HIERARCHY,
                tree=False,
                tree_title=None,
                src_data=True,
                folders=["anat", "func"],
                dry_run=True,
            )

    assert len(caplog.records) == 5
    assert "run_level = who knows" in caplog.records[3].message

    HIERARCHY["run_level"] = "acquisition"  # fix what was broke


def test_download_bids_for_runlevel_bidsexporterror_exception_detected(
    tmp_path, caplog
):

    caplog.set_level(logging.DEBUG)

    ## create expected file
    # bids_path = Path(tmp_path) / "work/bids"
    # bids_path.mkdir(parents=True)
    # with open(bids_path / "dataset_description.json", "w") as jfp:
    #    json.dump(DATASET_DESCRIPTION, jfp)

    with patch(
        "flywheel_gear_toolkit.GearToolkitContext.client", return_value=Acquisition(),
    ):

        with patch(
            "utils.bids.download_run_level.download_bids_dir",
            side_effect=BIDSExportError("crash", "boom"),
        ):

            with patch(
                "utils.bids.download_run_level.validate_bids", return_value=0,
            ):

                gtk_context = flywheel_gear_toolkit.GearToolkitContext(
                    input_args=["-d aex:analysis"], gear_path=tmp_path
                )

                err_code = download_bids_for_runlevel(
                    gtk_context,
                    HIERARCHY,
                    tree=False,
                    tree_title=None,
                    src_data=True,
                    folders=["anat", "func"],
                    dry_run=True,
                )

    assert len(caplog.records) == 6
    assert "crash" in caplog.records[4].message


def test_download_bids_for_runlevel_validate_exception_detected(tmp_path, caplog):

    caplog.set_level(logging.DEBUG)

    HIERARCHY["run_level"] = "project"

    # create expected file
    bids_path = Path(tmp_path) / "work/bids"
    bids_path.mkdir(parents=True)
    with open(bids_path / "dataset_description.json", "w") as jfp:
        json.dump(DATASET_DESCRIPTION, jfp)

    with patch(
        "flywheel_gear_toolkit.GearToolkitContext.client", return_value=Acquisition(),
    ):

        with patch(
            "flywheel_gear_toolkit.GearToolkitContext.download_project_bids",
            return_value=bids_path,
        ):

            with patch(
                "utils.bids.download_run_level.validate_bids",
                side_effect=Exception("except", "what"),
            ):

                gtk_context = flywheel_gear_toolkit.GearToolkitContext(
                    input_args=["-d aex:analysis"], gear_path=tmp_path
                )

                err_code = download_bids_for_runlevel(
                    gtk_context,
                    HIERARCHY,
                    tree=False,
                    tree_title=None,
                    src_data=True,
                    folders=[],
                    dry_run=True,
                )

    assert len(caplog.records) == 9
    assert "('except', 'what')" in caplog.records[7].message

    HIERARCHY["run_level"] = "acquisition"  # fix what was broke


def test_download_bids_for_runlevel_nothing_downloaded_detected(tmp_path, caplog):

    caplog.set_level(logging.DEBUG)

    HIERARCHY["run_level"] = "subject"

    with patch(
        "flywheel_gear_toolkit.GearToolkitContext.client", return_value=Acquisition(),
    ):

        with patch(
            "flywheel_gear_toolkit.GearToolkitContext.download_project_bids",
            return_value="nowhere",
        ):

            gtk_context = flywheel_gear_toolkit.GearToolkitContext(
                input_args=["-d aex:analysis"], gear_path=tmp_path
            )

            err_code = download_bids_for_runlevel(
                gtk_context,
                HIERARCHY,
                tree=False,
                tree_title=None,
                src_data=True,
                folders=[],
                dry_run=True,
            )

    assert len(caplog.records) == 6
    assert "No BIDS data was found" in caplog.records[4].message

    HIERARCHY["run_level"] = "acquisition"  # fix what was broke
