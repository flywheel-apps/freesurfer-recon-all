"""Compress HTML files."""

import datetime
import glob
import logging
import os
import subprocess as sp

log = logging.getLogger(__name__)


def zip_it_zip_it_good(context, name):
    """ Compress html file into an appropriately named archive file *.html.zip
    files are automatically shown in another tab in the browser. These are
    saved at the top level of the output folder."""

    name_no_html = name[:-5]  # remove ".html" from end

    dest_zip = os.path.join(
        context.output_dir, name_no_html + "_" + context.destination["id"] + ".html.zip"
    )

    log.info('Creating viewable archive "' + dest_zip + '"')

    command = ["zip", "-q", dest_zip, "index.html"]
    result = sp.run(command, check=True)


def zip_htmls(context, path):
    """ Zip all .html files at the given path so they can be displayed
        on the Flywheel platform.
        Each html file must be converted into an archive individually:
          rename each to be "index.html", then create a zip archive from it.
    """

    log.info("Creating viewable archives for all html files")

    if os.path.exists(path):

        log.info("Found path: " + str(path))

        os.chdir(path)

        html_files = glob.glob("*.html")

        if len(html_files) > 0:

            # if there is an index.html, do it first and re-name it for safe
            # keeping
            save_name = ""
            if os.path.exists("index.html"):
                log.info("Found index.html")
                zip_it_zip_it_good(context, "index.html")

                now = datetime.datetime.now()
                save_name = now.strftime("%Y-%m-%d_%H-%M-%S") + "_index.html"
                os.rename("index.html", save_name)

                html_files.remove("index.html")  # don't do this one later

            for h_file in html_files:
                os.rename(h_file, "index.html")
                zip_it_zip_it_good(context, h_file)
                os.rename("index.html", h_file)

            # reestore if necessary
            if save_name != "":
                os.rename(save_name, "index.html")

        else:
            log.warning("No *.html files at " + str(path))

    else:

        log.error("Path NOT found: " + str(path))
