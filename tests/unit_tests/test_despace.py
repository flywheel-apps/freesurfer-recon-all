"""Unit test for despace"""

import os
import logging
from pathlib import Path

from utils.fly.despace import despace


DIRS = ['look-in-me', "look-in-me/a dir with spaces"]
FILES = ["look-in-me/a dir with spaces/afile", "look-in-me/a dir with spaces/afile with spaces"]


def print_captured(captured):

    print("\nout")
    for ii, msg in enumerate(captured.out.split("\n")):
        print(f"{ii:2d} {msg}")
    print("\nerr")
    for ii, msg in enumerate(captured.err.split("\n")):
        print(f"{ii:2d} {msg}")


def test_despace_works(capsys, tmp_path):

    for adir in DIRS:
        print(f"creating dir  '{tmp_path}/{adir}'")
        Path(tmp_path / adir).mkdir(parents=True)

    for afile in FILES:
        print(f"creating file '{tmp_path}/{afile}'")
        Path(tmp_path / afile).touch()

    despace(tmp_path / DIRS[0])

    found = [f for f in Path(tmp_path / DIRS[0]).rglob("*")]
    #for ff in found:
    #    print(ff)
    
    assert found[0].name == "a_dir_with_spaces"
    assert found[2].name == "afile_with_spaces"

    #captured = capsys.readouterr()
    #print_captured(captured)
