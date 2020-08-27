#!/usr/bin/env python3
"""Run the gear: set up for and call command-line command."""

import os
import sys
import shutil
import json
from pathlib import Path

import flywheel_gear_toolkit
from flywheel_gear_toolkit.licenses.freesurfer import install_freesurfer_license
from flywheel_gear_toolkit.interfaces.command_line import build_command_list
from flywheel_gear_toolkit.interfaces.command_line import exec_command
from flywheel_gear_toolkit.utils.zip_tools import zip_output, unzip_archive

from utils.bids.run_level import get_run_level_and_hierarchy
from utils.bids.download_run_level import download_bids_for_runlevel
from utils.fly.despace import despace
from utils.fly.make_file_name_safe import make_file_name_safe
from utils.dry_run import pretend_it_ran
from utils.results.zip_htmls import zip_htmls
from utils.results.zip_intermediate import zip_all_intermediate_output
from utils.results.zip_intermediate import zip_intermediate_selected


GEAR = "freesurfer-recon-all"
REPO = "flywheel-apps"
CONTAINER = f"{REPO}/{GEAR}]"


FREESURFER_HOME = "/opt/freesurfer"
LICENSE_FILE = FREESURFER_HOME + "/license.txt"


def main(gtk_context):

    fw = gtk_context.client

    log = gtk_context.log

    config = gtk_context.config

    subjects_dir = "/opt/freesurfer/subjects"

    anat_dir = gtk_context.get_input_path("anatomical")
    anat_dir_2 = gtk_context.get_input_path("t1w_anatomical_2")
    anat_dir_3 = gtk_context.get_input_path("t1w_anatomical_3")
    anat_dir_4 = gtk_context.get_input_path("t1w_anatomical_4")
    anat_dir_5 = gtk_context.get_input_path("t1w_anatomical_5")
    t2_dir = gtk_context.get_input_path("t2w_anatomical")

    # Keep a list of errors and warning to print all in one place at end of log
    # Any errors will prevent the command from running and will cause exit(1)
    errors = []
    warnings = []

    # Given the destination container, figure out if running at the project,
    # subject, or session level.
    hierarchy = get_run_level_and_hierarchy(fw, gtk_context.destination["id"])

    # This is the label of the project, subject or session and is used
    # as part of the name of the output files.
    run_label = make_file_name_safe(hierarchy["run_label"])

    # Output will be put into a directory named as the destination id.
    # This allows the raw output to be deleted so that a zipped archive
    # can be returned.
    output_analysisid_dir = gtk_context.output_dir / gtk_context.destination["id"]

    # get # cpu's to set -openmp
    os_cpu_count = str(os.cpu_count())
    log.info("os.cpu_count() = %s", os_cpu_count)
    n_cpus = config.get("n_cpus")
    if n_cpus:
        del config["n_cpus"]
        if n_cpus > os_cpu_count:
            log.warning("n_cpus > number available, using %d", os_cpu_count)
            config["openmp"] = os_cpu_count
        elif n_cpus == 0:
            log.info("n_cpus == 0, using %d (maximum available)", os_cpu_count)
            config["openmp"] = os_cpu_count
    else:  # Default is to use all cpus available
        config["openmp"] = os_cpu_count  # zoom zoom

    # grab environment for gear (saved in Dockerfile)
    with open("/tmp/gear_environ.json", "r") as f:
        environ = json.load(f)

        # Add environment to log if debugging
        kv = ""
        for k, v in environ.items():
            kv += k + "=" + v + " "
        log.debug("Environment: " + kv)

    # get config for command by skipping gear config parameters
    command_config = {}
    for key, val in config.items():
        if not key.startswith("gear-"):
            command_config[key] = val
    # print("command_config:", json.dumps(command_config, indent=4))

    # Validate the command parameter dictionary - make sure everything is
    # ready to run so errors will appear before launching the actual gear
    # code.  Add descriptions of problems to errors & warnings lists.
    # print("gtk_context.config:", json.dumps(gtk_context.config, indent=4))

    # The main command line command to be run:
    command = ["recon-all"]

    # This is also used as part of the name of output files
    command_name = make_file_name_safe(command[0])

    if Path(LICENSE_FILE).exists():
        log.debug("%s exists.", LICENSE_FILE)
    install_freesurfer_license(gtk_context, LICENSE_FILE)

    # recon-all can be run in one of three ways:
    # 1) re-running a previous run (if .zip file is provided)
    # 2) on BIDS formatted data determined by the run level (project, subject, session)
    # 3) by providing anatomical files as input to the gear

    # Check for previous freesurfer run
    find = [f for f in Path(anat_dir).rglob("freesurfer-recon-all*.zip")]
    if len(find) == 0:
        existing_run = False
    else:
        if len(find) > 1:
            log.warning(
                "Found %d previous freesurfer runs. Using first", len(find)
            )
        fs_archive = find[0]
        existing_run = True
        unzip_archive(fs_archive, subjects_dir)
        try:
            zip = zipfile.ZipFile(
                config["inputs"]["anatomical"]["location"]["path"]
            )
            subject_id = zip.namelist()[0].split("/")[0]
        except:
            subject_id = ""
        if subject_id == "":
            if config.get("subject_id"):
                subject_id = config["config"]["subject_id"]
        else:
            subject_id = fw.get_analysis(
                gtk_context.destination["id"]
            ).parents.subject
            subject = fw.get_subject(subject_id)
            subject_id = subject.label
        subject_id = make_file_name_safe(subject_id)
        if not Path(subjects_dir / subject_id).exists():
            log.critical(
                "%s  No SUBJECT DIR could be found! Cannot continue. Exiting",
                CONTAINER,
            )
        log.info(
            "%s  recon-all running from previous run...(recon-all -subjid %s %s",
            subject_id,
            recon_all_opts,
            CONTAINER,
        )
        # recon-all -subjid "${SUBJECT_ID}" ${RECON_ALL_OPTS}
        command.append("-subjid")
        command.append(subject_id)

    if not existing_run and len(errors) == 0 and config.get("gear-bids"):

        # 3 positional args: bids path, output dir, 'participant'
        # This should be done here in case there are nargs='*' arguments
        # These follow the BIDS Apps definition (https://github.com/BIDS-Apps)
        command.append(str(gtk_context.work_dir / "bids"))
        command.append(str(output_analysisid_dir))
        command.append("participant")

        # Create HTML file that shows BIDS "Tree" like output?
        tree = True
        tree_title = f"{command_name} BIDS Tree"

        # Whether or not to include src data (e.g. dicoms) when downloading BIDS
        src_data = False

        # Limit download to specific folders? e.g. ['anat','func','fmap']
        # when downloading BIDS
        folders = []  # empty list is no limit

        error_code = download_bids_for_runlevel(
            gtk_context,
            hierarchy,
            tree=tree,
            tree_title=tree_title,
            src_data=src_data,
            folders=folders,
            dry_run=gtk_context.config.get("gear-dry-run"),
            do_validate_bids=gtk_context.config.get("gear-run-bids-validation"),
        )
        if error_code > 0 and not gtk_context.config.get("gear-ignore-bids-errors"):
            errors.append(f"BIDS Error(s) detected.  Did not run {CONTAINER}")

        # now that work/bids/ exists, copy in the ignore file
        bidsignore_path = gtk_context.get_input_path("bidsignore")
        if bidsignore_path:
            shutil.copy(bidsignore_path, "work/bids/.bidsignore")
            log.info("Installed .bidsignore in work/bids/")
        existing_run = True

    if not existing_run and len(errors) == 0:
        # Check for input files: anatomical NIfTI or DICOM archive
        despace(anat_dir)

    # Don't run if there were errors or if this is a dry run
    ok_to_run = True

    if len(errors) > 0:
        ok_to_run = False
        returncode = 1
        log.info("Command was NOT run because of previous errors.")

    if gtk_context.config.get("gear-dry-run"):
        ok_to_run = False
        returncode = 0
        e = "gear-dry-run is set: Command was NOT run."
        log.warning(e)
        warnings.append(e)
        pretend_it_ran(gtk_context)

    try:

        if ok_to_run:

            returncode = 0

            # Create output directory
            log.info("Creating output directory %s", output_analysisid_dir)
            Path(output_analysisid_dir).mkdir()

            # add configuration parameters to the command
            command = build_command_list(command, command_config)
            single_dash_cmd = []
            for cmd in command:
                s_cmd = cmd.split("=")
                if s_cmd[0].startswith("--"):
                    single_dash_cmd.append(s_cmd[0][1:])
                else:
                    single_dash_cmd.append(s_cmd[0])
                if len(s_cmd) == 2:
                    if s_cmd[0].startswith("--"):
                        single_dash_cmd.append(s_cmd[1])
                    else:
                        log()
            command = single_dash_cmd
            log.info("command is: %s", str(command))

            # This is what it is all about
            exec_command(command, environ=environ)

    except RuntimeError as exc:
        returncode = 1
        errors.append(exc)
        log.critical(exc)
        log.exception("Unable to execute command.")

    finally:

        # Cleanup, move all results to the output directory

        # TODO
        # see https://github.com/bids-standard/pybids/tree/master/examples
        # for any necessary work on the bids files inside the gear, perhaps
        # to query results or count stuff to estimate how long things will take.
        # Add that to utils/results.py

        # zip entire output/<analysis_id> folder into
        #  <gear_name>_<project|subject|session label>_<analysis.id>.zip
        zip_file_name = (
            gtk_context.manifest["name"]
            + f"_{run_label}_{gtk_context.destination['id']}.zip"
        )
        zip_output(
            str(gtk_context.output_dir),
            gtk_context.destination["id"],
            zip_file_name,
            dry_run=False,
            exclude_files=None,
        )

        # zip any .html files in output/<analysis_id>/
        zip_htmls(gtk_context, output_analysisid_dir)

        # possibly save ALL intermediate output
        if gtk_context.config.get("gear-save-intermediate-output"):
            zip_all_intermediate_output(gtk_context, run_label)

        # possibly save intermediate files and folders
        zip_intermediate_selected(gtk_context, run_label)

        # clean up: remove output that was zipped
        if Path(output_analysisid_dir).exists():
            if not gtk_context.config.get("gear-keep-output"):

                log.debug('removing output directory "%s"', str(output_analysisid_dir))
                shutil.rmtree(output_analysisid_dir)

            else:
                log.info(
                    'NOT removing output directory "%s"', str(output_analysisid_dir)
                )

        else:
            log.info("Output directory does not exist so it cannot be removed")

        # Report errors and warnings at the end of the log so they can be easily seen.
        if len(warnings) > 0:
            msg = "Previous warnings:\n"
            for err in warnings:
                if str(type(err)).split("'")[1] == "str":
                    # show string
                    msg += "  Warning: " + str(err) + "\n"
                else:  # show type (of warning) and warning message
                    err_type = str(type(err)).split("'")[1]
                    msg += f"  {err_type}: {str(err)}\n"
            log.info(msg)

        if len(errors) > 0:
            msg = "Previous errors:\n"
            for err in errors:
                if str(type(err)).split("'")[1] == "str":
                    # show string
                    msg += "  Error msg: " + str(err) + "\n"
                else:  # show type (of error) and error message
                    err_type = str(type(err)).split("'")[1]
                    msg += f"  {err_type}: {str(err)}\n"
            log.info(msg)
            returncode = 1

    return returncode


if __name__ == "__main__":

    gtk_context = flywheel_gear_toolkit.GearToolkitContext()

    # Setup basic logging and log the configuration for this job
    if gtk_context["gear-log-level"] == "INFO":
        gtk_context.init_logging("info")
    else:
        gtk_context.init_logging("debug")
    gtk_context.log_config()

    exit_status = main(gtk_context)

    gtk_context.log.info("%s Gear is done.  Returning %s", CONTAINER, exit_status)

    sys.exit(exit_status)
