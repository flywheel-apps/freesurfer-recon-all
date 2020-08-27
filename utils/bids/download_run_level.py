#!/usr/bin/env python3
"""A robust template for accessing BIDS formatted data."""

import json
import logging
from pathlib import Path

from flywheel import ApiException
from flywheel_bids.export_bids import download_bids_dir

from utils.bids.errors import BIDSExportError

from .tree import tree_bids
from .validate import validate_bids

log = logging.getLogger(__name__)

DATASET_DESCRIPTION = {
    "Acknowledgements": "",
    "Authors": [],
    "BIDSVersion": "1.2.0",
    "DatasetDOI": "",
    "Funding": [],
    "HowToAcknowledge": "",
    "License": "",
    "Name": "tome",
    "ReferencesAndLinks": [],
    "template": "project",
}


def fix_dataset_description(bids_path):
    """Make sure dataset_description.json exists and that "Funding" is a list.

    If these are not true, BIDS validation will fail.

    The flywheel bids template had (or has, unless it has been fixed), the
    default dataset_description.json file with "Funding" as an empty string.

    But the BIDS standard requires "Funding" and a list so the validator
    will error out and prevent BIDS Apps from running.

    This fixes that by checking to make sure it is a list and if not,
    converting it to a list and then writing the file back out.

    Args:
        bids_path (string): path to bids formatted data.

    Note:
        If dataset_description.json does not exist, it will be created
    """

    validator_file = Path(bids_path) / "dataset_description.json"

    need_to_write = False

    if validator_file.exists():

        with open(validator_file) as json_file:

            data = json.load(json_file)

            log.info("type of Funding is: %s", str(type(data["Funding"])))

            if not isinstance(data["Funding"], list):

                log.warning('data["Funding"] is not a list')
                data["Funding"] = list(data["Funding"])
                log.info("changed it to: %s", str(type(data["Funding"])))

                need_to_write = True

    else:
        log.info("Creating default dataset_description.json file")
        data = DATASET_DESCRIPTION
        need_to_write = True

    if need_to_write:
        with open(validator_file, "w") as outfile:
            json.dump(data, outfile)


def download_bids_for_runlevel(
    gtk_context,
    hierarchy,
    tree=False,
    tree_title=None,
    src_data=False,
    folders=[],
    dry_run=False,
    do_validate_bids=True,
):
    """Figure out run level, download BIDS, validate BIDS, tree work/bids.

    Args:
        gtk_context (gear_toolkit.GearToolkitContext): flywheel gear context
        hierarchy (dict): containing the run_level and labels for the
            run_label, group, project, subject, session, and
            acquisition.
        tree (boolean): create HTML page in output showing 'tree' of bids data
        src_data (boolean): download source data (dicoms) as well
        folders (list): only include the listed folders, if empty include all.
        dry_run (boolean): don't actually download data if True

    Returns:
        err_code (int): tells a bit about the error:
            0    - no error
            1..9 - error code returned by bids validator
            10   - BIDS validation errors were detected
            11   - the validator could not be run
            12   - TypeError while analyzing validator output
            20   - running at wrong level
            21   - BIDSExportError
            22   - validator exception
            23   - attempt to download unknown acquisition
            24   - destination does not exist
            25   - download_bids_dir() ApiException
            26   - no BIDS data was downloaded

    Note: information on BIDS "folders" (used to limit what is downloaded)
    can be found at https://bids-specification.readthedocs.io/en/stable/99-appendices/04-entity-table.html.
    """

    extra_tree_text = ""  # Text to be added to the end of the tree HTML file

    run_level = hierarchy["run_level"]

    # Show the complete destination hierarchy in the tree html ouput for
    # clarity
    extra_tree_text += f"run_level is {run_level}\n"
    for key, val in hierarchy.items():
        extra_tree_text += f"  {key:<18}: {val}\n"
    extra_tree_text += f'  {"folders":<18}: {folders}\n'
    if src_data:
        extra_tree_text += f'  {"source data?":<18}: downloaded\n'
    else:
        extra_tree_text += f'  {"source data?":<18}: not downloaded\n'
    if dry_run:
        extra_tree_text += f'  {"dry run?":<18}: Yes\n'
    else:
        extra_tree_text += f'  {"dry run?":<18}: No\n'
    extra_tree_text += "\n"

    if run_level == "no_destination":
        msg = "Destination does not exist."
        log.critical(msg)
        extra_tree_text += f"ERROR: {msg}\n"
        bids_path = None
        err_code = 24  # destination does not exist

    else:

        if gtk_context.destination["type"] == "analysis":
            pass

        elif gtk_context.destination["type"] == "acquisition":
            log.info("Destination is acquisition, changing run_level to " "acquisition")
            acquisition = gtk_context.client.get_acquisition(
                gtk_context.destination["id"]
            )
            hierarchy["acquisition_label"] = acquisition.label
            extra_tree_text += (
                f'  {"acquisition_label":<18}: changed to ' + f"{acquisition.label}\n\n"
            )
            run_level = "acquisition"

        else:
            log.info(
                'The destination "%s" is not an analysis or acquisition.',
                gtk_context.destination["type"],
            )

        try:  # download BIDS data for the proper run level

            if src_data:
                log.info("Downloading source data.")
            else:
                log.info("Not downloading source data.")

            if dry_run:
                log.info("Dry run is set.  No data will be downloaded.")
            else:
                log.info("Dry run is NOT set.  Data WILL be downloaded.")

            if len(folders) > 0:
                log.info("Downloading BIDS only in folders: %s", folders)
            else:
                log.info("Downloading BIDS data in all folders.")

            BIDS_DIR = Path(gtk_context.work_dir) / "bids"

            if run_level == "project":

                log.info(
                    'Downloading BIDS for project "%s"', hierarchy["project_label"]
                )

                if Path(BIDS_DIR).exists():
                    bids_path = BIDS_DIR
                    log.info(f"Not actually downloading it because {BIDS_DIR} exists")
                else:
                    # don't filter by subject or session, grab all
                    bids_path = gtk_context.download_project_bids(
                        src_data=src_data, folders=folders, dry_run=dry_run
                    )

            elif run_level == "subject":

                log.info(
                    'Downloading BIDS for subject "%s"', hierarchy["subject_label"]
                )

                if Path(BIDS_DIR).exists():
                    bids_path = BIDS_DIR
                    log.info(f"Not actually downloading it because {BIDS_DIR} exists")
                else:
                    # only download this subject
                    bids_path = gtk_context.download_project_bids(
                        src_data=src_data,
                        folders=folders,
                        dry_run=dry_run,
                        subjects=[hierarchy["subject_label"]],
                    )

            elif run_level == "session":

                log.info(
                    'Downloading BIDS for session "%s"', hierarchy["session_label"]
                )

                if Path(BIDS_DIR).exists():
                    bids_path = BIDS_DIR
                    log.info(f"Not actually downloading it because {BIDS_DIR} exists")
                else:
                    # only download data for this session AND this subject
                    bids_path = gtk_context.download_project_bids(
                        src_data=src_data,
                        folders=folders,
                        dry_run=dry_run,
                        subjects=[hierarchy["subject_label"]],
                        sessions=[hierarchy["session_label"]],
                    )

            elif run_level == "acquisition":

                if hierarchy["acquisition_label"] == "unknown acqusition":
                    msg = (
                        'Cannot download BIDS for acquisition "'
                        + hierarchy["acquisition_label"]
                        + '"'
                    )
                    log.critical(msg)
                    extra_tree_text += f"ERROR: {msg}\n"
                    bids_path = None
                    err_code = 23  # attempt to download unknown acquisition

                else:
                    log.info(
                        'Downloading BIDS for acquisition "%s"',
                        hierarchy["acquisition_label"],
                    )

                    bids_path = BIDS_DIR
                    if Path(BIDS_DIR).exists():
                        log.info(
                            "Not actually downloading it because " f"{BIDS_DIR} exists"
                        )
                    else:
                        # only download acquisition data
                        download_bids_dir(
                            gtk_context.client,
                            gtk_context.destination["id"],
                            "acquisition",
                            BIDS_DIR,
                            src_data=src_data,
                            folders=folders,
                            dry_run=dry_run,
                        )

            else:
                msg = (
                    "This job is not being run at the project, subject, "
                    + f"session or acquisition level. run_level = {run_level}"
                )
                log.critical(msg, exc_info=True)
                extra_tree_text += f"ERROR: {msg}\n"
                bids_path = None
                err_code = 20

        except BIDSExportError as bidserr:
            log.critical(bidserr, exc_info=True)
            extra_tree_text += f"{bidserr}\n"
            bids_path = None
            err_code = 21

        except ApiException as err:
            log.exception(err, exc_info=True)
            extra_tree_text += f"EXCEPTION: {err}\n"
            bids_path = None
            err_code = 25  # download_bids_dir() ApiException

    if bids_path:  # then validate it

        if Path(bids_path).exists():
            log.info("Found BIDS path %s", str(bids_path))

            # Make sure "Funding" is a list or validation will fail
            fix_dataset_description(bids_path)

            try:
                if do_validate_bids:
                    # validate (assume returns 1.. something <10 on error)
                    err_code = validate_bids(bids_path)
                else:
                    log.info("Not running BIDS validation")
                    err_code = 0

            except Exception as exc:
                log.exception(exc, exc_info=True)
                extra_tree_text += f"EXCEPTION: {exc}\n"
                err_code = 22

        else:  # Nothing was downloaded, so what's the point?
            msg = "No BIDS data was found to download"
            log.critical(msg)
            extra_tree_text += f"{msg}\n"
            err_code = 26  # no BIDS data was downloaded

    else:
        # try the usual path in case it was partially created
        bids_path = Path("work/bids")
        extra_tree_text += f"Warning: no bids path, checked work/bids anyway.\n"

    if err_code > 0:
        msg = "Error in BIDS download or validation.  See log for details."
        log.error(msg)
        extra_tree_text += f"{msg}\n"
        # do not bother processing BIDS data

    else:
        msg = "Downloading BIDS data was successful!"
        log.info(msg)
        extra_tree_text += msg

    if tree:
        tree_bids(
            bids_path,
            str(Path(gtk_context.output_dir) / "bids_tree"),
            tree_title,
            extra_tree_text,
        )

    return err_code
