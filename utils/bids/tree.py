"""Gears might want to see how the BIDS data looks when it is processed.

Example:
    .. code-block:: python

        from pathlib import Path


        bids_path = Path('work/bids')

        tree_bids(bids_path, 'tree_output')

    Produces an HTML file with `tree` like output for the path "work/bids".
"""

import logging
from pathlib import Path

log = logging.getLogger(__name__)


def tree_bids(directory, base_name, title=None, extra=None):
    """Write `tree` output as html file for the given path.

    ".html" will be appended to base_name to create the
    file name to use for the result.

    Args:
        directory (path): path to a directory to display.
        base_name (str): file name (without ".html") to write output to.
        title (str): title to put in html file.
        extra (str): extra text to add at the end.
    """

    if directory is None:
        directory = Path("(unknown)")

    if title is None:
        title = ""

    with open(base_name + ".html", "w") as html_file:

        html1 = (
            '<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 '
            'Transitional//EN">\n'
            + "<html>\n"
            + "  <head>\n"
            + '    <meta http-equiv="content-type" content="text/html; '
            'charset=UTF-8">\n'
            + "    <title>tree "
            + directory.name
            + "</title>\n"
            + "  </head>\n"
            + "  <body>\n"
            + "  <h1>"
            + title
            + "</h1>\n"
            + "  <b>"
            + directory.name
            + "</b>\n"
            + "<pre>\n"
        )
        html_file.write(html1)

        dir_str = str(directory) + "/"

        log.info('Getting "tree" listing of %s', dir_str)

        html_file.write(dir_str + "\n")

        num_dirs = 0
        num_files = 0

        for path in sorted(directory.rglob("*")):

            depth = len(path.relative_to(directory).parts)
            spacer = "    " * depth

            # print(f'{depth:02d} {spacer}+ {path.name}')

            if path.is_file():
                num_files += 1
                html_file.write(f"{spacer}{path.name}\n")
            else:
                num_dirs += 1
                html_file.write(f"{spacer}{path.name}/\n")

        html_file.write(f"{num_dirs} directories, {num_files} files\n")

        if extra:
            html_file.write(f"\n{extra}\n")

        html2 = "</pre>\n" + "    </blockquote>\n" + "  </body>\n" + "</html>\n"
        html_file.write(html2)

    log.info('Wrote "%s.html"', base_name)
