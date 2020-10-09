"""Unit test for remove_i_args"""

import logging

from run import remove_i_args


def test_remove_i_args_works(capsys):

    command = [
        "time",
        "recon-all",
        "-i",
        "path/to/that/T1",
        "-all",
        "-whatever",
        "hey",
        "-i",
        "another/path/to/input/scan",
        "-3T",
    ]
    print(command)

    resume_command = remove_i_args(command)
    print(resume_command)

    assert "-i" not in resume_command
    assert resume_command == ["time", "recon-all", "-all", "-whatever", "hey", "-3T"]
