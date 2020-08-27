"""Unit test for running tree system command"""

import logging
from os import chdir
from pathlib import Path

from utils.bids.tree import tree_bids


def test_tree_bids_basic_results_works(caplog, tmp_path):
    """Make sure tree output actually happens."""

    caplog.set_level(logging.DEBUG)

    bids_path = Path("work/bids")

    the_temp_dir = tmp_path / Path(bids_path)
    the_temp_dir.mkdir(parents=True)
    chdir(str(tmp_path))

    Path("work/bids/adir").mkdir()
    Path("work/bids/adir/anotherfiile.json").touch()
    Path("work/bids/afile.txt").touch()
    Path("work/bids/anotherdir").mkdir()
    Path("work/bids/anotherdir/README.md").touch()

    tree_bids(bids_path, "tree_out")

    with open("tree_out.html") as tfp:
        html = tfp.read().split("\n")

    # for lll,line in enumerate(html):
    #     print(f'{lll:02} {line}')
    # print(caplog.records)

    assert len(caplog.records) == 2
    assert Path("tree_out.html").exists()
    assert html[10] == "work/bids/"  # has trailing '/'
    assert html[16] == "2 directories, 3 files"
    assert caplog.records[1].message == 'Wrote "tree_out.html"'


def test_tree_bids_directory_none_title_extra_work(caplog, tmp_path):
    """Test when directory is none, when title and extra are given."""

    caplog.set_level(logging.DEBUG)

    bids_path = Path("work/bids")

    the_temp_dir = tmp_path / Path(bids_path)
    the_temp_dir.mkdir(parents=True)
    chdir(str(tmp_path))

    Path("work/bids/adir").mkdir()
    Path("work/bids/adir/anotherfiile.json").touch()
    Path("work/bids/afile.txt").touch()
    Path("work/bids/anotherdir").mkdir()
    Path("work/bids/anotherdir/README.md").touch()

    tree_bids(None, "tree_out", title="Bozo", extra="huge shoes")

    with open("tree_out.html") as tfp:
        html = tfp.read().split("\n")

    # for lll,line in enumerate(html):
    #     print(f'{lll:02} {line}')
    # print(caplog.records)

    assert len(caplog.records) == 2
    assert Path("tree_out.html").exists()
    assert html[7] == "  <h1>Bozo</h1>"
    assert html[10] == "(unknown)/"
    assert html[11] == "0 directories, 0 files"
    assert html[13] == "huge shoes"
    assert caplog.records[1].message == 'Wrote "tree_out.html"'
