import logging
import os
import shutil

log = logging.getLogger(__name__)


def despace(directory):
    """Remove spaces in file and directory names in entire directory tree.

    Args:
        directory (PosixPath): work in this directory
    """

    for root, dirs, files in os.walk(directory, topdown=False):
        for dd in dirs:
            if " " in dd:
                new = dd.replace(" ", "_")
                log.debug(f"'{root}/{dd}' -> '{root}/{new}'")
                shutil.move(f"{root}/{dd}", f"{root}/{new}")
        for ff in files:
            if " " in ff:
                new = ff.replace(" ", "_")
                log.debug(f"'{root}/{ff}' -> '{root}/{new}'")
                shutil.move(f"{root}/{ff}", f"{root}/{new}")
