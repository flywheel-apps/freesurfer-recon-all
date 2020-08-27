"""Unit test for running BIDS validation"""

import json
import logging
import subprocess as sp
from os import chdir
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from utils.bids.validate import validate_bids

DATA_ROOT = Path("tests/data").resolve()


@pytest.fixture(scope="function")
def json_file():
    def get_json_file(name):
        return DATA_ROOT / Path("validator." + name + ".json")

    return get_json_file


def test_validate_bids_basic_results_works(caplog, tmp_path, json_file):

    caplog.set_level(logging.DEBUG)

    bids_path = Path("work/bids")
    ret = sp.CompletedProcess
    ret.stderr = None
    ret.returncode = 0

    result_json = json_file("basic")

    # Must create directory or validate.py will error on opening
    # output file
    the_temp_dir = tmp_path / Path(bids_path)
    the_temp_dir.mkdir(parents=True)
    chdir(str(tmp_path))

    # Before patching open() read the jason file that is simulated results
    with open(result_json) as jfp:
        bids_output = json.load(jfp)

    with patch("utils.bids.validate.sp.run") as mock_run:
        with patch("__main__.open", MagicMock()):
            with patch(
                "utils.bids.validate.json.load", MagicMock(side_effect=[bids_output])
            ):

                mock_run.return_value = ret

                err_code = validate_bids(bids_path)

                assert err_code == 0
                assert len(caplog.records) == 7
                assert caplog.records[6].message == "No BIDS errors detected."


def test_validate_bids_no_bids_output(caplog, tmp_path, json_file):

    caplog.set_level(logging.DEBUG)

    bids_path = Path("work/bids")
    ret = sp.CompletedProcess
    ret.stderr = None
    ret.returncode = 1

    # Must create directory or validate.py will error on opening
    # output file
    the_temp_dir = tmp_path / Path(bids_path)
    the_temp_dir.mkdir(parents=True)
    chdir(str(tmp_path))

    with patch("utils.bids.validate.sp.run") as mock_run:
        with patch("__main__.open", MagicMock()):
            with patch("utils.bids.validate.json.load", MagicMock(side_effect=[""])):

                mock_run.return_value = ret

                err_code = validate_bids(bids_path)

                assert err_code == 11
                assert len(caplog.records) == 5
                assert caplog.records[4].message == "BIDS validation could not run."


def test_validate_bids_non_zero_exit_reported(caplog, tmp_path, json_file):
    """Simulate a failure of running the bids validator such that it
    returns output which breaks the json.load()."""

    caplog.set_level(logging.DEBUG)

    bids_path = Path("work/bids")
    ret = sp.CompletedProcess
    ret.returncode = 1

    # Must create directory or validate.py will error on opening
    # output file
    the_temp_dir = tmp_path / Path(bids_path)
    the_temp_dir.mkdir(parents=True)
    chdir(str(tmp_path))

    with patch("utils.bids.validate.sp.run") as mock_run:

        mock_run.return_value = ret

        err_code = validate_bids(bids_path)

        assert err_code == 11
        assert len(caplog.records) == 7
        assert "JSONDecodeError" in caplog.records[3].message


def test_validate_bids_error_results_exception(caplog, tmp_path, json_file):

    caplog.set_level(logging.DEBUG)

    bids_path = Path("work/bids")
    ret = sp.CompletedProcess
    ret.stderr = None
    ret.returncode = 0

    result_json = json_file("error")

    # Must create directory or validate.py will error on opening
    # output file
    the_temp_dir = tmp_path / Path(bids_path)
    the_temp_dir.mkdir(parents=True)
    chdir(str(tmp_path))

    # Before patching open() read the jason file that is results
    with open(result_json) as jfp:
        bids_output = json.load(jfp)

    with patch("utils.bids.validate.sp.run") as mock_run:
        with patch("__main__.open", MagicMock()):
            with patch(
                "utils.bids.validate.json.load", MagicMock(side_effect=[bids_output])
            ):

                mock_run.return_value = ret

                err_code = validate_bids(bids_path)

                assert err_code == 10
                assert len(caplog.records) == 8
                assert (
                    caplog.records[7].message
                    == "1 BIDS validation error(s) were detected."
                )


def test_validate_bids_called_process_error(caplog, tmp_path, json_file):
    """This one actually runs bids-validator so skip it if it is not installed"""

    caplog.set_level(logging.DEBUG)

    completed_process = sp.run("which bids-validator", shell=True)
    if completed_process.returncode != 0:
        pytest.skip("bids-validator is not installed")

    bids_path = Path("work/bids")

    # Must create directory or validate.py will error on opening
    # output file
    the_temp_dir = tmp_path / Path(bids_path)
    the_temp_dir.mkdir(parents=True)
    chdir(str(tmp_path))

    # Nothing is in the directory, which is a problem, eh?

    err_code = validate_bids(bids_path)

    assert err_code == 10
    assert len(caplog.records) == 6
    assert "Quick validation failed" in caplog.records[4].message
