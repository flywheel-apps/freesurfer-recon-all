"""Unit tests for run_level.py"""

import json
import logging
from os import chdir
from pathlib import Path
from unittest.mock import MagicMock, patch

import flywheel

from utils.bids.run_level import get_run_level_and_hierarchy


class Acquisition:
    def __init__(self):
        self.label = "TheAcquisitionLabel"


class Session:
    def __init__(self):
        self.label = "TheSessionLabel"


class Subject:
    def __init__(self):
        self.label = "TheSubjectCode"


class Project:
    def __init__(self):
        self.label = "TheProjectLabel"


class Parent:
    def __init__(self, level):
        self.type = level


class Destination:
    def __init__(self, level):
        self.parent = Parent(level)
        self.parents = {
            "group": "monkeyshine",
            "project": "proj_id",
            "subject": "subj_id",
            "session": "sess_id",
            "acquisition": "acq_id",
        }

    def get(self, level, none):
        return self.parent


class FW:
    def __init__(self, level):
        self.destination = Destination(level)

    def get(self, id):
        if id == "01234":
            ret = self.destination
        elif id == "proj_id":
            ret = Project()
        elif id == "subj_id":
            ret = Subject()
        elif id == "sess_id":
            ret = Session()
        elif id == "acq_id":
            ret = Acquisition()
        return ret


def test_run_level_project_works(caplog):
    """Running at project level means subject, session, and acquisition are undefined."""

    caplog.set_level(logging.DEBUG)

    fw = FW("project")
    fw.destination.parents["subject"] = None
    fw.destination.parents["session"] = None
    fw.destination.parents["acquisition"] = None

    hierarchy = get_run_level_and_hierarchy(fw, "01234")

    print(caplog.records)

    assert hierarchy["run_level"] == "project"
    assert hierarchy["group"] == "monkeyshine"
    assert len(caplog.records) == 6
    assert "run_level = project" in caplog.records[0].message
    assert "monkeyshine" in caplog.records[1].message
    assert "TheProjectLabel" in caplog.records[2].message
    assert "subject_label = unknown subject" in caplog.records[3].message
    assert "session_label = unknown session" in caplog.records[4].message
    assert "acquisition_label = unknown acquisition" in caplog.records[5].message


def test_run_level_subject_works(caplog):
    """Running at subject level means session, and acquisition are undefined."""

    caplog.set_level(logging.DEBUG)

    fw = FW("subject")
    fw.destination.parents["session"] = None
    fw.destination.parents["acquisition"] = None

    hierarchy = get_run_level_and_hierarchy(fw, "01234")

    print(caplog.records)

    assert hierarchy["run_level"] == "subject"
    assert len(caplog.records) == 6
    assert "run_level = subject" in caplog.records[0].message
    assert "monkeyshine" in caplog.records[1].message
    assert "TheProjectLabel" in caplog.records[2].message
    assert "subject_label = TheSubjectCode" in caplog.records[3].message
    assert "session_label = unknown session" in caplog.records[4].message
    assert "acquisition_label = unknown acquisition" in caplog.records[5].message


def test_run_level_session_works(caplog):
    """Running at session level means acquisition is undefined."""

    caplog.set_level(logging.DEBUG)

    fw = FW("session")
    fw.destination.parents["acquisition"] = None

    hierarchy = get_run_level_and_hierarchy(fw, "01234")

    print(caplog.records)

    assert hierarchy["run_level"] == "session"
    assert len(caplog.records) == 6
    assert "run_level = session" in caplog.records[0].message
    assert "monkeyshine" in caplog.records[1].message
    assert "TheProjectLabel" in caplog.records[2].message
    assert "subject_label = TheSubjectCode" in caplog.records[3].message
    assert "session_label = TheSessionLabel" in caplog.records[4].message
    assert "acquisition_label = unknown acquisition" in caplog.records[5].message


def test_run_level_acquisition_works(caplog):
    """Running at acquisition level means everything is defined."""

    caplog.set_level(logging.DEBUG)

    fw = FW("acquisition")

    hierarchy = get_run_level_and_hierarchy(fw, "01234")

    print(caplog.records)

    assert hierarchy["run_level"] == "acquisition"
    assert len(caplog.records) == 6
    assert "run_level = acquisition" in caplog.records[0].message
    assert "monkeyshine" in caplog.records[1].message
    assert "TheProjectLabel" in caplog.records[2].message
    assert "subject_label = TheSubjectCode" in caplog.records[3].message
    assert "session_label = TheSessionLabel" in caplog.records[4].message
    assert "acquisition_label = TheAcquisitionLabel" in caplog.records[5].message


def test_run_level_no_parent_says_so(caplog):
    """Running on an acquisition as a destination e.g. (on ss.ce.flywheel.io):

    run_level = no_parent,  job.id = 5c92a228c488760025dc699f
    classifier acquisition  dicom-mr-classifier 0.8.2
         {'id': 'thadbrown@flywheel.io', 'type': 'user'}
    job.destination = {'id': '5c929faeb33891002dc06903', 'type': 'acquisition'}
    parent  None
    parents {'acquisition': None,
    'analysis': None,
    'group': 'scien',
    'project': '5dc48947bd690a002bdaa0c9',
    'session': '5dc48debbd690a0029da9fd7',
    'subject': '5dc48debbd690a0022da9fbe'}
    """

    caplog.set_level(logging.DEBUG)

    fw = FW("acquisition")
    fw.destination.parent = None

    hierarchy = get_run_level_and_hierarchy(fw, "01234")
    print(f"run_level = {hierarchy['run_level']}")
    print(f"hierarchy  = {json.dumps(hierarchy, indent=4)}")
    print(caplog.records)

    assert hierarchy["run_level"] == "no_parent"


def test_run_level_no_project_says_so(caplog):
    """A destination that has no parent probably never happens"""

    caplog.set_level(logging.DEBUG)

    fw = FW("acquisition")
    fw.destination.parent = None

    hierarchy = get_run_level_and_hierarchy(fw, "01234")

    assert hierarchy["run_level"] == "no_parent"


def test_run_level_unknown_project_says_so(caplog):
    """a destination that has no project id in parents probably never happens"""

    caplog.set_level(logging.DEBUG)

    fw = FW("acquisition")
    fw.destination.parents["project"] = None

    hierarchy = get_run_level_and_hierarchy(fw, "01234")

    assert "unknown project" in caplog.records[2].message


def test_run_level_exception_handled(caplog):

    caplog.set_level(logging.DEBUG)

    with patch(
        "flywheel.Client.get",
        MagicMock(side_effect=flywheel.ApiException("foo", "fum")),
    ):

        fw = flywheel.Client

        hierarchy = get_run_level_and_hierarchy(fw, "01234")

        print(caplog.records)

        assert "Unable to get level and hierarchy" in caplog.records[0].message
