"""Unit test for set_core_count"""

import logging
import os
from pathlib import Path

from run import set_core_count

log = logging.getLogger(__name__)


def test_core_count_empty_works(capsys):

    config = dict()

    set_core_count(config, log)

    assert config["openmp"] == os.cpu_count()


def test_core_count_0_gets_max(capsys):

    config = {"n_cpus": 0}

    set_core_count(config, log)

    print(config)

    assert config["openmp"] == os.cpu_count()


def test_core_count_tomuch_gets_max(capsys):

    config = {"n_cpus": 1000}

    set_core_count(config, log)

    print(config)

    assert config["openmp"] == os.cpu_count()


def test_core_count_1_gets_1(capsys):

    config = {"n_cpus": 1}

    set_core_count(config, log)

    print(config)

    assert config["openmp"] == 1
