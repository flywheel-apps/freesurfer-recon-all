"""Save files from work/, compressed in output/."""

import logging
import os
import subprocess as sp

log = logging.getLogger(__name__)


def zip_intermediate_selected(context, run_label):
    """
    Find all of the listed files and folders in the "work/" directory and zip
    them into one archive.
    """

    do_find = False
    files = []
    folders = []
    # get list of intermediate files (if any)
    if context.config.get("gear-intermediate-files", None):
        if len(context.config["gear-intermediate-files"]) > 0:
            files = context.config["gear-intermediate-files"].split()
            log.debug(str(files))
            do_find = True

    # get list of intermediate folders (if any)
    if context.config.get("gear-intermediate-folders", None):
        if len(context.config["gear-intermediate-folders"]) > 0:
            folders = context.config["gear-intermediate-folders"].split()
            do_find = True

    if do_find:

        # Name of zip file has <subject> and <analysis>
        analysis_id = context.destination["id"]
        gear_name = context.manifest["name"]
        file_name = f"{gear_name}_work_selected_{run_label}_{analysis_id}.zip"
        dest_zip = os.path.join(context.output_dir, file_name)

        os.chdir(context.work_dir)

        log.info('Files and folders will be zipped to "' + dest_zip + '"')

        files_found = []
        folders_found = []
        for subdir, walk_dirs, walk_files in os.walk("."):

            for ff in walk_files:
                if ff in files:
                    path = os.path.join(subdir, ff)
                    if os.path.exists(path):
                        files_found.append(ff)
                        log.info("Zipping file:   " + path)
                        command = ["zip", "-q", dest_zip, path]
                        result = sp.run(command, check=True)
                    else:
                        log.error("Missing file:   " + path)

            for ff in walk_dirs:
                if ff in folders:
                    folders_found.append(ff)
                    path = os.path.join(subdir, ff)
                    if os.path.exists(path):
                        log.info("Zipping folder: " + path)
                        command = ["zip", "-q", "-r", dest_zip, path]
                        result = sp.run(command, check=True)
                    else:
                        log.error("Missing folder:   " + path)
        for ff in files:
            if ff not in files_found:
                log.error(f"Could not find file '{ff}'")
        for ff in folders:
            if ff not in folders_found:
                log.error(f"Could not find folder '{ff}'")
    else:
        log.debug("No files or folders specified in config to zip")


def zip_all_intermediate_output(context, run_label):
    """
    Zip all intermediate output in the "work/ directory into one archive.
    """

    # Name of zip file has <subject> and <analysis>
    analysis_id = context.destination["id"]
    gear_name = context.manifest["name"]
    file_name = f"{gear_name}_work_{run_label}_{analysis_id}.zip"
    dest_zip = os.path.join(context.output_dir, file_name)

    work_path, work_dir = os.path.split(context.work_dir)
    os.chdir(work_path)

    log.info("Zipping " + work_dir + " directory to " + dest_zip + ".")

    command = ["zip", "-q", "-r", dest_zip, work_dir]
    result = sp.run(command, check=True)
