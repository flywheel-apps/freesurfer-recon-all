#!/usr/bin/env python3
"""Run the gear: set up for and call command-line command."""

import json
import os
import sys
import zipfile
from pathlib import Path

import flywheel_gear_toolkit
from flywheel_gear_toolkit.interfaces.command_line import exec_command
from flywheel_gear_toolkit.licenses.freesurfer import install_freesurfer_license
from flywheel_gear_toolkit.utils.zip_tools import unzip_archive, zip_output

from utils.dry_run import pretend_it_ran
from utils.fly.despace import despace
from utils.fly.make_file_name_safe import make_file_name_safe

GEAR = "freesurfer-recon-all"
REPO = "flywheel-apps"
CONTAINER = f"{REPO}/{GEAR}"

FLYWHEEL_BASE = Path("/flywheel/v0")
OUTPUT_DIR = Path(FLYWHEEL_BASE / "output")
INPUT_DIR = Path(FLYWHEEL_BASE / "input")

SUBJECTS_DIR = Path("/usr/local/freesurfer/subjects")
FREESURFER_HOME = "/usr/local/freesurfer"
LICENSE_FILE = FREESURFER_HOME + "/license.txt"


def do_gear_hippocampal_subfields(subject_id, mri_dir, dry_run, environ, log):

    log.info("Starting segmentation of hippocampal subfields...")
    cmd = ["segmentHA_T1.sh", subject_id]
    exec_command(cmd, environ=environ, dry_run=dry_run, cont_output=True)
    txt_files = [
        "lh.hippoSfVolumes-T1.v21.txt",
        "rh.hippoSfVolumes-T1.v21.txt",
        "lh.amygNucVolumes-T1.v21.txt",
        "rh.amygNucVolumes-T1.v21.txt",
    ]
    for tf in txt_files:
        cmd = [
            "tr",
            "' '",
            ",",
            "<",
            f"{mri_dir}/{tf}",
            ">",
            f"{OUTPUT_DIR}/{subject_id}_{tf.replace('.txt','.csv')}",
        ]
        exec_command(
            cmd, environ=environ, shell=True, dry_run=dry_run, cont_output=True
        )


def do_gear_brainstem_structures(subject_id, mri_dir, dry_run, environ, log):

    log.info("Starting segmentation of brainstem subfields...")
    cmd = ["segmentBS.sh", subject_id]
    exec_command(cmd, environ=environ, dry_run=dry_run, cont_output=True)
    cmd = [
        "quantifyBrainstemStructures.sh",
        f"{mri_dir}/brainstemSsVolumes.v2.txt",
    ]
    exec_command(cmd, environ=environ, dry_run=dry_run, cont_output=True)
    cmd = [
        "tr",
        "' '",
        ",",
        "<",
        f"{mri_dir}/brainstemSsVolumes.v2.txt",
        ">",
        f"{OUTPUT_DIR}/{subject_id}_brainstemSsVolumes.v2.csv",
    ]
    exec_command(cmd, environ=environ, shell=True, dry_run=dry_run, cont_output=True)


def do_gear_register_surfaces(subject_id, dry_run, environ, log):

    log.info("Running surface registrations...")
    # Register hemispheres
    cmd = ["xhemireg", "--s", subject_id]
    exec_command(cmd, environ=environ, dry_run=dry_run, cont_output=True)
    # Register the left hemisphere to fsaverage_sym
    cmd = ["surfreg", "--s", subject_id, "--t", "fsaverage_sym", "--lh"]
    exec_command(cmd, environ=environ, dry_run=dry_run, cont_output=True)
    # Register the inverted right hemisphere to fsaverage_sym
    cmd = [
        "surfreg",
        "--s",
        subject_id,
        "--t",
        "fsaverage_sym",
        "--lh",
        "--xhemi",
    ]
    exec_command(cmd, environ=environ, dry_run=dry_run, cont_output=True)


def do_gear_convert_surfaces(subject_dir, dry_run, environ, log):
    """ Convert selected surfaces in subject/surf to obj in output."""

    log.info("Converting surfaces to object (.obj) files...")
    surf_dir = f"{subject_dir}/surf"
    surfaces = [
        "lh.pial",
        "rh.pial",
        "lh.white",
        "rh.white",
        "rh.inflated",
        "lh.inflated",
    ]
    for surf in surfaces:
        cmd = [
            "mris_convert",
            f"{surf_dir}/{surf}",
            f"{surf_dir}/{surf}.asc",
        ]
        exec_command(cmd, environ=environ, dry_run=dry_run, cont_output=True)
        cmd = [
            f"{FLYWHEEL_BASE}/utils/srf2obj",
            f"{surf_dir}/{surf}.asc",
            ">",
            f"{OUTPUT_DIR}/{surf}.obj",
        ]
        exec_command(
            cmd, environ=environ, shell=True, dry_run=dry_run, cont_output=True
        )


def do_gear_convert_volumes(config, mri_dir, dry_run, environ, log):
    """Convert select volumes in subject/mri to nifti."""

    log.info("Converting volumes to NIfTI files...")
    mri_mgz_files = [
        "aparc+aseg.mgz",
        "aparc.a2009s+aseg.mgz",
        "brainmask.mgz",
        "lh.ribbon.mgz",
        "rh.ribbon.mgz",
        "ribbon.mgz",
        "aseg.mgz",
        "orig.mgz",
        "T1.mgz",
    ]
    if config.get("gear-hippocampal_subfields"):
        mri_mgz_files += [
            "lh.hippoAmygLabels-T1.v21.FSvoxelSpace.mgz",
            "rh.hippoAmygLabels-T1.v21.FSvoxelSpace.mgz",
        ]
    if config.get("gear-brainstem_structures"):
        mri_mgz_files += ["brainstemSsLabels.v12.FSvoxelSpace.mgz"]
    for ff in mri_mgz_files:
        cmd = [
            "mri_convert",
            "-i",
            f"{mri_dir}/{ff}",
            "-o",
            f"{OUTPUT_DIR}/{ff.replace('.mgz', '.nii.gz')}",
        ]
        exec_command(cmd, environ=environ, dry_run=dry_run, cont_output=True)


def do_gear_convert_stats(subject_id, dry_run, environ, log):
    """Write aseg stats to a table."""

    log.info("Exporting stats files csv...")
    cmd = [
        "asegstats2table",
        "-s",
        subject_id,
        "--delimiter",
        "comma",
        f"--tablefile={OUTPUT_DIR}/{subject_id}_aseg_stats_vol_mm3.csv",
    ]
    exec_command(cmd, environ=environ, dry_run=dry_run, cont_output=True)

    # Parse the aparc files and write to table
    hemi = ["lh", "rh"]
    parc = ["aparc.a2009s", "aparc", "aparc.DKTatlas", "aparc.pial"]
    for hh in hemi:
        for pp in parc:
            cmd = [
                "aparcstats2table",
                "-s",
                subject_id,
                f"--hemi={hh}",
                f"--delimiter=comma",
                f"--parc={pp}",
                f"--tablefile={OUTPUT_DIR}/{subject_id}_{hh}_{pp}"
                + "_stats_area_mm2.csv",
            ]
            exec_command(cmd, environ=environ, dry_run=dry_run, cont_output=True)


def main(gtk_context):

    fw = gtk_context.client

    log = gtk_context.log

    config = gtk_context.config
    dry_run = config.get("gear-dry-run")

    anat_dir = INPUT_DIR / "anatomical"
    anat_dir_2 = INPUT_DIR / "t1w_anatomical_2"
    anat_dir_3 = INPUT_DIR / "t1w_anatomical_3"
    anat_dir_4 = INPUT_DIR / "t1w_anatomical_4"
    anat_dir_5 = INPUT_DIR / "t1w_anatomical_5"
    t2_dir = INPUT_DIR / "t2w_anatomical"

    # Keep a list of errors and warning to print all in one place at end of log
    # Any errors will prevent the command from running and will cause exit(1)
    errors = []
    warnings = []

    # get # cpu's to set -openmp
    os_cpu_count = os.cpu_count()
    log.info("os.cpu_count() = %d", os_cpu_count)
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
    print("command_config:", json.dumps(command_config, indent=4))

    # Validate the command parameter dictionary - make sure everything is
    # ready to run so errors will appear before launching the actual gear
    # code.  Add descriptions of problems to errors & warnings lists.
    # print("gtk_context.config:", json.dumps(gtk_context.config, indent=4))

    # The main command line command to be run:
    command = ["time", "recon-all"]

    if Path(LICENSE_FILE).exists():
        log.debug("%s exists.", LICENSE_FILE)
    install_freesurfer_license(gtk_context, LICENSE_FILE)

    subject_id = config.get("subject_id")
    if not subject_id:
        subject_id = fw.get_analysis(gtk_context.destination["id"]).parents.subject
        subject = fw.get(subject_id)
        subject_id = subject.label

    # recon-all can be run in two ways:
    # 1) re-running a previous run (if .zip file is provided)
    # 2) by providing anatomical files as input to the gear

    # 1) Check for previous freesurfer run
    find = [f for f in anat_dir.rglob("freesurfer-recon-all*.zip")]
    if len(find) == 0:
        existing_run = False
    else:
        log.debug("subject_id 0 %s", subject_id)
        if len(find) > 1:
            log.warning("Found %d previous freesurfer runs. Using first", len(find))
        fs_archive = find[0]
        existing_run = True
        unzip_archive(str(fs_archive), SUBJECTS_DIR)
        try:
            zipit = zipfile.ZipFile(fs_archive)
            subject_id = zipit.namelist()[0].split("/")[0]
            log.debug("subject_id 1 %s", subject_id)
        except:
            subject_id = ""
        if subject_id == "":
            if config.get("subject_id"):
                subject_id = config["config"]["subject_id"]
                log.debug("subject_id 2 %s", subject_id)
        else:
            subject_id = fw.get_analysis(gtk_context.destination["id"]).parents.subject
            subject = fw.get_subject(subject_id)
            subject_id = subject.label
            log.debug("subject_id 3 %s", subject_id)
        subject_id = make_file_name_safe(subject_id)
        if not Path(SUBJECTS_DIR / subject_id).exists():
            log.critical("No SUBJECT DIR could be found! Cannot continue. Exiting")
            sys.exit(1)
        log.info(
            "recon-all running from previous run...(recon-all -subjid %s)", subject_id,
        )
        # recon-all -subjid "${SUBJECT_ID}" ${RECON_ALL_OPTS}
        command.append("-subjid")
        command.append(subject_id)

    # 2) provide anatomical files as input to the gear
    if not existing_run and len(errors) == 0:
        # Check for input files: anatomical NIfTI or DICOM archive
        despace(anat_dir)
        anatomical_list = [f for f in anat_dir.rglob("*.nii*")]
        if len(anatomical_list) == 1:
            anatomical = str(anatomical_list[0])

        elif len(anatomical_list) == 0:
            # assume a directory of DICOM files was provided
            # find all regular files that are not hidden and are not in a hidden
            # directory.  Like this bash command:
            # ANATOMICAL=$(find $INPUT_DIR/* -not -path '*/\.*' -type f | head -1)
            anatomical_list = [
                f
                for f in INPUT_DIR.rglob("[!.]*")
                if "/." not in str(f) and f.is_file()
            ]

            if len(anatomical_list) == 0:
                log.critical(
                    "Anatomical input could not be found in %s! Exiting (1)",
                    str(anat_dir),
                )
                os.system(f"ls -lRa {str(anat_dir)}")
                sys.exit(1)

            anatomical = str(anatomical_list[0])
            if anatomical.endswith(".zip"):
                dicom_dir = anat_dir / "dicoms"
                dicom_dir.mkdir()
                unzip_archive(anatomical, dicom_dir)
                despace(dicom_dir)
                anatomical_list = [
                    f
                    for f in dicom_dir.rglob("[!.]*")
                    if "/." not in str(f) and f.is_file()
                ]
                anatomical = str(anatomical_list[0])

        else:
            log.warning("What?  Found %s NIfTI files!", len(anatomical_list))

        log.info("anatomical is '%s'", anatomical)

        # Process additional anatomical inputs
        add_inputs = ""
        for anat_dir in (anat_dir_2, anat_dir_3, anat_dir_4, anat_dir_5):
            if anat_dir.is_dir():
                despace(anat_dir)
                anatomical_list = [f for f in anat_dir.rglob("*.nii*") if f.is_file()]
                if len(anatomical_list) > 0:
                    log.info(
                        "Adding %s to the processing stream...", anatomical_list[0]
                    )
                    add_inputs += f"-i {str(anatomical_list[0])} "

        # T2 input file
        if t2_dir.is_dir():
            despace(t2_dir)
            anatomical_list = [f for f in t2_dir.rglob("*.nii*") if f.is_file()]
            if len(anatomical_list) > 0:
                log.info("Adding T2 %s to the processing stream...", anatomical_list[0])
                add_inputs += f"-T2 {str(anatomical_list[0])} "

        add_inputs = add_inputs[:-1]  # so split below won't add extra empty string

        command.append("-i")
        command.append(anatomical)
        if add_inputs:
            command += [ww for ww in add_inputs.split(" ")]
        command.append("-subjid")
        command.append(subject_id)

    subject_dir = Path(SUBJECTS_DIR / subject_id)
    work_dir = Path(gtk_context.output_dir / subject_id)
    if not work_dir.is_symlink():
        work_dir.symlink_to(subject_dir)

    if "subject_id" in command_config:  # this was already handled
        command_config.pop("subject_id")

    # add configuration parameters to the command
    for key, val in command_config.items():
        # print(f"key:{key} val:{val} type:{type(val)}")
        if key == "reconall_options":
            command += [ww for ww in val.split(" ")]
        elif isinstance(val, bool):
            if val:
                command.append(f"-{key}")
        else:
            command.append(f"-{key}")
            command.append(f"{val}")

    log.info("command is: %s", str(command))

    return_code = 0

    try:

        if len(errors) > 0:
            log.info("Command was NOT run because of previous errors.")
            return_code = 1

        else:

            if dry_run:
                e = "gear-dry-run is set: Command was NOT run."
                log.warning(e)
                warnings.append(e)
                pretend_it_ran(gtk_context)

            else:
                # This is what it is all about
                exec_command(command, environ=environ, shell=True, cont_output=True)

            # Optional Segmentations
            mri_dir = f"{subject_dir}/mri"

            if config.get("gear-hippocampal_subfields"):
                do_gear_hippocampal_subfields(
                    subject_id, mri_dir, dry_run, environ, log
                )

            if config.get("gear-brainstem_structures"):
                do_gear_brainstem_structures(subject_id, mri_dir, dry_run, environ, log)

            if config.get("gear-register_surfaces"):
                do_gear_register_surfaces(subject_id, dry_run, environ, log)

            if config.get("gear-convert_surfaces"):
                do_gear_convert_surfaces(subject_dir, dry_run, environ, log)

            if config.get("gear-convert_volumes"):
                do_gear_convert_volumes(config, mri_dir, dry_run, environ, log)

            if config.get("gear-convert_stats"):
                do_gear_convert_stats(subject_id, dry_run, environ, log)

    except RuntimeError as exc:
        errors.append(exc)
        log.critical(exc)
        log.exception("Unable to execute command.")
        return_code = 1

    finally:

        # Cleanup, move all results to the output directory

        # zip entire output/<subject_id> folder into
        #  <gear_name>_<subject_id>_<analysis.id>.zip
        zip_file_name = (
            gtk_context.manifest["name"]
            + f"_{subject_id}_{gtk_context.destination['id']}.zip"
        )
        zip_output(
            str(gtk_context.output_dir),
            subject_id,
            zip_file_name,
            dry_run=False,
            exclude_files=None,
        )

        # clean up: remove output that was zipped
        output_analysisid_dir = gtk_context.output_dir / subject_id
        if Path(output_analysisid_dir).exists():
            if not gtk_context.config.get("gear-all-output"):

                log.debug('removing output directory "%s"', str(output_analysisid_dir))
                output_analysisid_dir.unlink()

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

        gtk_context.log.info("%s Gear is done.  Returning 0", CONTAINER)

        sys.exit(return_code)


if __name__ == "__main__":

    gtk_context = flywheel_gear_toolkit.GearToolkitContext()

    # Setup basic logging and log the configuration for this job
    if gtk_context.config["gear-log-level"] == "INFO":
        gtk_context.init_logging("info")
    else:
        gtk_context.init_logging("debug")
    gtk_context.log_config()

    main(gtk_context)
