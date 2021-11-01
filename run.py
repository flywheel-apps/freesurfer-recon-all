#!/usr/bin/env python3
"""Run the gear: set up for and call command-line command."""

import json
import os
import sys
import zipfile
from pathlib import Path

import flywheel_gear_toolkit
import pandas as pd
from flywheel_gear_toolkit.interfaces.command_line import exec_command
from flywheel_gear_toolkit.licenses.freesurfer import install_freesurfer_license
from flywheel_gear_toolkit.utils.zip_tools import unzip_archive, zip_output

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


def set_core_count(config, log):
    """get # cpu's to set -openmp by setting config["openmp"]

    Args:
        config (GearToolkitContext.config): config dictionary from config.json
        log (GearToolkitContext.log): logger set up by Gear Toolkit
    """

    os_cpu_count = os.cpu_count()
    log.info("os.cpu_count() = %d", os_cpu_count)
    n_cpus = config.get("n_cpus")
    if n_cpus:
        del config["n_cpus"]
        if n_cpus > os_cpu_count:
            log.warning("n_cpus > number available, using max %d", os_cpu_count)
            config["openmp"] = os_cpu_count
        else:
            log.info("n_cpus using %d from config", n_cpus)
            config["openmp"] = n_cpus
    else:  # Default is to use all cpus available
        config["openmp"] = os_cpu_count  # zoom zoom
        log.info("using n_cpus = %d (maximum available)", os_cpu_count)


def check_for_previous_run(log):
    """Check for .zip file that contains subject from a previous run.

    Args:
        log (GearToolkitContext.log): logger set up by Gear Toolkit

    Returns:
        new_subject_id (str)
    """

    new_subject_id = ""  # assume not going to find zip file

    anat_dir = INPUT_DIR / "anatomical"
    find = list(anat_dir.rglob("freesurfer-recon-all*.zip"))
    if len(find) > 0:
        if len(find) > 1:
            log.warning("Found %d previous freesurfer runs. Using first", len(find))
        fs_archive = find[0]
        unzip_archive(str(fs_archive), SUBJECTS_DIR)
        try:
            zipit = zipfile.ZipFile(fs_archive)
            new_subject_id = zipit.namelist()[0].split("/")[0]
            log.debug("new_subject_id %s", new_subject_id)
        except:
            new_subject_id = ""

        if new_subject_id != "":
            new_subject_id = make_file_name_safe(new_subject_id)
            if not Path(SUBJECTS_DIR / new_subject_id).exists():
                log.critical("No SUBJECT DIR could be found! Cannot continue. Exiting")
                sys.exit(1)
            log.info(
                "recon-all running from previous run...(recon-all -subjid %s)",
                new_subject_id,
            )

    return new_subject_id


def get_input_file(log):
    """Provide required anatomical file as input to the gear.

    Input file can be either a NIfTI file or a DICOM archive.

    Args:
        log (GearToolkitContext.log): logger set up by Gear Toolkit

    Returns:
        anatomical (str): path to anatomical file
    """

    anat_dir = INPUT_DIR / "anatomical"
    despace(anat_dir)

    anatomical_list = list(anat_dir.rglob("*.nii*"))
    if len(anatomical_list) == 1:
        anatomical = str(anatomical_list[0])

    elif len(anatomical_list) == 0:
        # assume a directory of DICOM files was provided
        # find all regular files that are not hidden and are not in a hidden
        # directory.  Like this bash command:
        # ANATOMICAL=$(find $INPUT_DIR/* -not -path '*/\.*' -type f | head -1)
        anatomical_list = [
            f for f in INPUT_DIR.rglob("[!.]*") if "/." not in str(f) and f.is_file()
        ]

        if len(anatomical_list) == 0:
            log.critical(
                "Anatomical input could not be found in %s! Exiting (1)", str(anat_dir),
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
        anatomical = str(anatomical_list[0])

    log.info("anatomical is '%s'", anatomical)

    return anatomical


def get_additional_inputs(log):
    """Process additional anatomical inputs.

    Additional T1 and T2 input files must all be NIfTI (.nii or .nii.gz)

    Args:
        log (GearToolkitContext.log): logger set up by Gear Toolkit

    Returns:
        add_inputs (str): arguments to pass in for additional input files
    """

    add_inputs = ""

    # additional T1 input files
    anat_dir_2 = INPUT_DIR / "t1w_anatomical_2"
    anat_dir_3 = INPUT_DIR / "t1w_anatomical_3"
    anat_dir_4 = INPUT_DIR / "t1w_anatomical_4"
    anat_dir_5 = INPUT_DIR / "t1w_anatomical_5"
    for anat_dir in (anat_dir_2, anat_dir_3, anat_dir_4, anat_dir_5):
        if anat_dir.is_dir():
            despace(anat_dir)
            anatomical_list = [f for f in anat_dir.rglob("*.nii*") if f.is_file()]
            if len(anatomical_list) > 0:
                log.info("Adding %s to the processing stream...", anatomical_list[0])
                add_inputs += f"-i {str(anatomical_list[0])} "

    # T2 input file
    t2_dir = INPUT_DIR / "t2w_anatomical"
    if t2_dir.is_dir():
        despace(t2_dir)
        anatomical_list = [f for f in t2_dir.rglob("*.nii*") if f.is_file()]
        if len(anatomical_list) > 0:
            log.info("Adding T2 %s to the processing stream...", anatomical_list[0])
            add_inputs += f"-T2 {str(anatomical_list[0])} "

    add_inputs = add_inputs.rstrip()  # so split below won't add extra empty string

    return add_inputs


def generate_command(subject_id, command_config, log):
    """Compose the shell command to run recon-all.

    Args:
        subject_id (str): Freesurfer subject directory name
        command_config (dict): configuration parameters and values to pass in
        log (GearToolkitContext.log): logger set up by Gear Toolkit

    Returns:
        command (list of str): the command line to be run
    """
    # The main command line command to be run:
    command = ["time", "recon-all"]

    # recon-all can be run in two ways:
    # 1) re-running a previous run (if .zip file is provided)
    # 2) by providing anatomical files as input to the gear

    new_subject_id = check_for_previous_run(log)
    if new_subject_id:
        subject_id = new_subject_id
        command.append("-subjid")
        command.append(subject_id)

    else:
        anatomical = get_input_file(log)
        command.append("-i")
        command.append(anatomical)
        add_inputs = get_additional_inputs(log)
        if add_inputs:
            command += add_inputs.split(" ")
        command.append("-subjid")
        command.append(subject_id)

    # add configuration parameters to the command
    for key, val in command_config.items():
        # print(f"key:{key} val:{val} type:{type(val)}")
        if key == "reconall_options":
            command += val.split(" ")
        elif isinstance(val, bool):
            if val:
                command.append(f"-{key}")
        else:
            command.append(f"-{key}")
            command.append(f"{val}")

    log.info("command is: %s", str(command))

    return command


def remove_i_args(command):
    """Remove -i <path> arguments from command.

    Args:
        command (list of str): the command to run recon-all

    Returns:
        resume_command (list of str): same as command but without -i <arg>
    """

    resume_command = []

    skip_arg = False
    for arg in command:
        if arg == "-i":
            skip_arg = True  # and don't append
        elif skip_arg:
            skip_arg = False  # it is hereby skipped
        else:
            resume_command.append(arg)

    return resume_command


def do_gear_hippocampal_subfields(subject_id, mri_dir, dry_run, environ, metadata, log):
    """Run segmentHA_T1.sh and convert results to .csv files

    Args:
        subject_id (str): Freesurfer subject directory name
        mri_dir (str): the "mri" directory in the subject directory
        dry_run (boolean): actually do it or do everything but
        environ (dict): shell environment saved in Dockerfile
        metadata (dict): will be written to .metadata.json when gear finishes
        log (GearToolkitContext.log): logger set up by Gear Toolkit

    Returns:
        Nothing.
    """

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
        tablefile = f"{OUTPUT_DIR}/{subject_id}_{tf.replace('.txt', '.csv')}"
        cmd = [
            "tr",
            "' '",
            ",",
            "<",
            f"{mri_dir}/{tf}",
            ">",
            tablefile,
        ]
        exec_command(
            cmd, environ=environ, shell=True, dry_run=dry_run, cont_output=True
        )

        # add those stats to metadata on the destination analysis container
        if Path(tablefile).exists():
            log.info("%s exists.  Adding to metadata.", tablefile)
            stats_df = pd.read_csv(tablefile, names=["struc", "measure"])
            dft = stats_df.transpose()
            dft.columns = dft.iloc[0]
            dft = dft[1:]
            stats_json = dft.drop(dft.columns[0], axis=1).to_dict("records")[0]
            metadata["analysis"]["info"][f"{tf.replace('.txt', '')}"] = stats_json
        else:
            log.info("%s is missing", tablefile)


def do_gear_brainstem_structures(subject_id, mri_dir, dry_run, environ, metadata, log):
    """Run quantifyBrainstemStructures.sh and convert output to .csv.

    Args:
        subject_id (str): Freesurfer subject directory name
        mri_dir (str): the "mri" directory in the subject directory
        dry_run (boolean): actually do it or do everything but
        environ (dict): shell environment saved in Dockerfile
        metadata (dict): will be written to .metadata.json when gear finishes
        log (GearToolkitContext.log): logger set up by Gear Toolkit

    Returns:
        Nothing.
    """

    log.info("Starting segmentation of brainstem subfields...")
    cmd = ["segmentBS.sh", subject_id]
    exec_command(cmd, environ=environ, dry_run=dry_run, cont_output=True)
    tablefile = f"{OUTPUT_DIR}/{subject_id}_brainstemSsVolumes.v2.csv"
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
        tablefile,
    ]
    exec_command(cmd, environ=environ, shell=True, dry_run=dry_run, cont_output=True)

    # add those stats to metadata on the destination analysis container
    if Path(tablefile).exists():
        stats_df = pd.read_csv(tablefile)
        stats_json = stats_df.drop(stats_df.columns[0], axis=1).to_dict("records")[0]
        metadata["analysis"]["info"]["brainstemSsVolumes.v2"] = stats_json


def do_gear_hypothalamic_subunits(subject_id, dry_run, environ, threads, log):
    """Run mri_segment_hypothalamic_subunits.sh

    Note:
        running on a single, unprocessed T1 is not supported here.
        See: https://surfer.nmr.mgh.harvard.edu/fswiki/HypothalamicSubunits
        The posteriors are not saved in this run to improve execution time

    Args:
        subject_id (str): Freesurfer subject directory name
        dry_run (boolean): actually do it or do everything but
        environ (dict): shell environment saved in Dockerfile
        threads (int): number of threads to run on
        log (GearToolkitContext.log): logger set up by Gear Toolkit

    Returns:
        Nothing.
    """

    log.info("Starting Segmentation of hypothalamic subunits...")
    cmd = ["mri_segment_hypothalamic_subunits", '--s', str(subject_id), "--threads", str(threads)]
    exec_command(cmd, environ=environ, dry_run=dry_run, cont_output=True)

    # These files are also created:
    # "/mri/hypothalamic_subunits_volumes.v1.csv",
    # "/stats/hypothalamic_subunits_volumes.v1.stats"


def do_gear_thalamic_nuclei(subject_id, mri_dir, dry_run, environ, metadata, log):
    """Run segmentThalamicNuclei.sh and convert output to .csv.

    Note:
        Using an additional FGATIR or DBS scan has not yet been implement here.
        See: https://surfer.nmr.mgh.harvard.edu/fswiki/ThalamicNuclei

    Args:
        subject_id (str): Freesurfer subject directory name
        mri_dir (str): the "mri" directory in the subject directory
        dry_run (boolean): actually do it or do everything but
        environ (dict): shell environment saved in Dockerfile
        metadata (dict): will be written to .metadata.json when gear finishes
        log (GearToolkitContext.log): logger set up by Gear Toolkit

    Returns:
        Nothing.
    """

    log.info("Starting segmentation of thalamic nuclei...")
    cmd = ["segmentThalamicNuclei.sh", subject_id]
    exec_command(cmd, environ=environ, dry_run=dry_run, cont_output=True)
    tablefile = f"{OUTPUT_DIR}/{subject_id}_ThalamicNuclei.v12.T1.volumes.csv"
    cmd = [
        "tr",
        "' '",
        ",",
        "<",
        f"{mri_dir}/ThalamicNuclei.v12.T1.volumes.txt",
        ">",
        tablefile,
    ]
    exec_command(cmd, environ=environ, shell=True, dry_run=dry_run, cont_output=True)

    # add those stats to metadata on the destination analysis container
    if Path(tablefile).exists():
        log.info("%s exists.  Adding to metadata.", tablefile)
        stats_df = pd.read_csv(tablefile, names=["struc", "measure"])
        dft = stats_df.transpose()
        dft.columns = dft.iloc[0]
        dft = dft[1:]
        stats_json = dft.drop(dft.columns[0], axis=1).to_dict("records")[0]
        metadata["analysis"]["info"]["ThalamicNuclei.v12.T1.volumes"] = stats_json
    else:
        log.info("%s is missing", tablefile)


def do_gear_register_surfaces(subject_id, dry_run, environ, log):
    """Runs xhemireg and surfreg.

    Args:
        subject_id (str): Freesurfer subject directory name
        dry_run (boolean): actually do it or do everything but
        environ (dict): shell environment saved in Dockerfile
        log (GearToolkitContext.log): logger set up by Gear Toolkit

    Returns:
        Nothing.
    """

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
    """Convert selected surfaces in subject/surf to obj in output.

    Args:
        subject_dir (str): Full path to Freesurfer subject directory
        dry_run (boolean): actually do it or do everything but
        environ (dict): shell environment saved in Dockerfile
        log (GearToolkitContext.log): logger set up by Gear Toolkit

    Returns:
        Nothing.
    """

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
    """Convert select volumes in subject/mri to nifti.

    Args:
        config (GearToolkitContext.config): config dictionary from config.json
        mri_dir (str): the "mri" directory in the subject directory
        dry_run (boolean): actually do it or do everything but
        environ (dict): shell environment saved in Dockerfile
        log (GearToolkitContext.log): logger set up by Gear Toolkit

    Returns:
        Nothing.
    """

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
    if config.get("gear-gtmseg"):
        mri_mgz_files += ["gtmseg.mgz"]
    if config.get("gear-thalamic_nuclei"):
        mri_mgz_files += [
            "ThalamicNuclei.v12.T1.mgz",
            "ThalamicNuclei.v12.T1.FSvoxelSpace.mgz",
        ]

    if config.get("gear-hypothalamic_subunits"):
        mri_mgz_files += [
            "hypothalamic_subunits_seg.v1.mgz",
        ]

    for ff in mri_mgz_files:
        cmd = [
            "mri_convert",
            "-i",
            f"{mri_dir}/{ff}",
            "-o",
            f"{OUTPUT_DIR}/{ff.replace('.mgz', '.nii.gz')}",
        ]
        exec_command(cmd, environ=environ, dry_run=dry_run, cont_output=True)


def do_gear_convert_stats(subject_id, dry_run, environ, metadata, log):
    """Write aseg stats to a table.

    Args:
        subject_id (str): Freesurfer subject directory name
        dry_run (boolean): actually do it or do everything but
        environ (dict): shell environment saved in Dockerfile
        metadata (dict): will be written to .metadata.json when gear finishes
        log (GearToolkitContext.log): logger set up by Gear Toolkit

    Returns:
        Nothing.
    """

    log.info("Exporting stats files csv...")
    tablefile = f"{OUTPUT_DIR}/{subject_id}_aseg_stats_vol_mm3.csv"
    cmd = [
        "asegstats2table",
        "-s",
        subject_id,
        "--delimiter",
        "comma",
        f"--tablefile={tablefile}",
    ]
    exec_command(cmd, environ=environ, dry_run=dry_run, cont_output=True)

    # add those stats to metadata on the destination analysis container
    if Path(tablefile).exists():
        aseg_stats_df = pd.read_csv(tablefile)
        as_json = aseg_stats_df.drop(aseg_stats_df.columns[0], axis=1).to_dict(
            "records"
        )[0]
        metadata["analysis"]["info"]["aseg_stats_vol_mm3"] = as_json

    # Parse the aparc files and write to table
    hemi = ["lh", "rh"]
    parc = ["aparc.a2009s", "aparc", "aparc.DKTatlas", "aparc.pial"]
    for hh in hemi:
        for pp in parc:
            tablefile = f"{OUTPUT_DIR}/{subject_id}_{hh}_{pp}_stats_area_mm2.csv"
            cmd = [
                "aparcstats2table",
                "-s",
                subject_id,
                f"--hemi={hh}",
                f"--delimiter=comma",
                f"--parc={pp}",
                f"--tablefile={tablefile}",
            ]
            exec_command(cmd, environ=environ, dry_run=dry_run, cont_output=True)

            if Path(tablefile).exists():
                aparc_stats_df = pd.read_csv(tablefile)
                ap_json = aparc_stats_df.drop(
                    aparc_stats_df.columns[0], axis=1
                ).to_dict("records")[0]
                metadata["analysis"]["info"][f"{hh}_{pp}_stats_area_mm2"] = ap_json


def do_gtmseg(subject_id, dry_run, environ, log):
    """After running recon-all, gtmseg can be run on the subject to create a high-resolution segmentation.

    Args:
        subject_id (str): Freesurfer subject directory name
        dry_run (boolean): actually do it or do everything but
        environ (dict): shell environment saved in Dockerfile
        log (GearToolkitContext.log): logger set up by Gear Toolkit

    Returns:
        Nothing.  Output will be in the Freesurfer subject directory.
    """

    log.info("Running gtmseg...")
    cmd = ["gtmseg", "--s", subject_id]
    exec_command(cmd, environ=environ, dry_run=dry_run, cont_output=True)


def execute_recon_all_command(command, environ, dry_run, subject_dir, log, metadata={}):
    """ execute the recon_all command

    Given a command generated from `generate_command()`, attempt to execute recon all.
    This function provides the correct metadata required for a "dry-run" of the gear
    and includes a retry routine.

    Args:
        command (list): a list of command parameters to be called
        environ (dict): environmental variables required to run recon-all
        dry_run (bool): determines if this will be a dry run of the command or not.
        subject_dir (Path): the location of the subject directory to save recon-all output to
        log: (GearToolkitContext.log): logger set up by Gear Toolkit
        metadata (dict): when a dry-run is performed, a metadata dict is generated for later
        gear function

    Returns:
        errors (list): a list of errors encountered when attempting to run
        warnings (list): a list of warnings
        return_code (int): determines if we completed successfully (0) or with errors (1)
        metadata (dict): the same metadata dict from input, only modified if dry-run is True

    """

    num_tries = 0
    errors = []
    warnings = []

    while num_tries < 2:

        return_code = 0

        try:
            num_tries += 1

            if dry_run:
                e = "gear-dry-run is set: Command was NOT run."
                log.warning(e)
                warnings.append(e)
                if not subject_dir.exists():
                    subject_dir.mkdir()
                    with open(subject_dir / "afile.txt", "w") as afp:
                        afp.write("Nothing to see here.")
                metadata = {
                    "analysis": {
                        "info": {
                            "dry_run": {
                                "How dry I am": "Say to Mister Temperance...."
                            }
                        }
                    }
                }

            # This is what it is all about
            exec_command(
                command,
                environ=environ,
                dry_run=dry_run,
                shell=True,
                cont_output=True,
            )
            break

        except RuntimeError as exc:
            errors.append(exc)
            log.critical(exc)
            log.exception("Unable to execute command.")
            return_code = 1
            command = remove_i_args(command)  # try again with -i <arg> removed

    return errors, warnings, return_code, metadata


def execute_postprocesing_command(config, environ, dry_run, subject_id, subject_dir, log, metadata={}):
    """ execute post processing commands

    attempts to run post-processing routines on a completed recon-all direectory.

    Args:
        config (dict): the gear config settings
        environ (dict): environmental variables required to run recon-all
        dry_run (bool): determines if this will be a dry run of the command or not.
        subject_id (str): the subject ID to use in this process
        subject_dir (Path): the location of the subject directory to save recon-all output to
        log: (GearToolkitContext.log): logger set up by Gear Toolkit
        metadata (dict): when a dry-run is performed, a metadata dict is generated for later
        gear function

    Returns:
        errors (list): a list of errors encountered when attempting to run
        return_code (int): determines if we completed successfully (0) or with errors (1)
        metadata (dict): the same metadata dict from input, only modified if dry-run is True

    """



    num_tries = 0

    errors = []
    while num_tries < 2:
        return_code = 0

        try:
            num_tries += 1
            # Optional Segmentations
            mri_dir = f"{subject_dir}/mri"

            if config.get("gear-hippocampal_subfields"):
                do_gear_hippocampal_subfields(
                    subject_id, mri_dir, dry_run, environ, metadata, log
                )

            if config.get("gear-brainstem_structures"):
                do_gear_brainstem_structures(
                    subject_id, mri_dir, dry_run, environ, metadata, log
                )

            if config.get("gear-thalamic_nuclei"):
                do_gear_thalamic_nuclei(
                    subject_id, mri_dir, dry_run, environ, metadata, log
                )

            if config.get("gear-hypothalamic_subunits"):
                do_gear_hypothalamic_subunits(
                    subject_id, dry_run, environ, config["openmp"], log,
                )

            if config.get("gear-register_surfaces"):
                do_gear_register_surfaces(subject_id, dry_run, environ, log)

            if config.get("gear-convert_surfaces"):
                do_gear_convert_surfaces(subject_dir, dry_run, environ, log)

            if config.get("gear-gtmseg"):
                do_gtmseg(subject_id, dry_run, environ, log)

            if config.get("gear-convert_volumes"):
                do_gear_convert_volumes(config, mri_dir, dry_run, environ, log)

            if config.get("gear-convert_stats"):
                do_gear_convert_stats(subject_id, dry_run, environ, metadata, log)

            break  # If here, no error so it did run

        except RuntimeError as exc:
            errors.append(exc)
            log.critical(exc)
            log.exception("Unable to execute command.")
            return_code = 1

    return errors, return_code, metadata


def main(gtk_context):
    config = gtk_context.config

    # Setup basic logging and log the configuration for this job
    if config["gear-log-level"] == "INFO":
        gtk_context.init_logging("info")
    else:
        gtk_context.init_logging("debug")
    gtk_context.log_config()
    log = gtk_context.log

    fw = gtk_context.client

    dry_run = config.get("gear-dry-run")

    # Keep a list of errors and warning to print all in one place at end of log
    # Any errors will prevent the command from running and will cause exit(1)
    errors = []
    warnings = []

    metadata = {"analysis": {"info": {}}}

    set_core_count(config, log)

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

    expert_path = gtk_context.get_input_path("expert")
    if expert_path:
        command_config["expert"] = expert_path

    # print("command_config:", json.dumps(command_config, indent=4))
    # Validate the command parameter dictionary - make sure everything is
    # ready to run so errors will appear before launching the actual gear
    # code.  Add descriptions of problems to errors & warnings lists.
    # print("gtk_context.config:", json.dumps(gtk_context.config, indent=4))

    if Path(LICENSE_FILE).exists():
        log.debug("%s exists.", LICENSE_FILE)
    install_freesurfer_license(gtk_context, LICENSE_FILE)

    subject_id = config.get("subject_id")
    if subject_id:
        log.debug("Got subject_id from config: %s", subject_id)
    else:
        subject_id = fw.get_analysis(gtk_context.destination["id"]).parents.subject
        subject = fw.get_subject(subject_id)
        subject_id = subject.label
        log.debug(
            "Got subject_id from destination's parent's subject's label:  %s",
            subject_id,
        )
    new_subject_id = make_file_name_safe(subject_id)
    if new_subject_id != subject_id:
        log.warning(
            "'%s' has non-file-name-safe characters in it!  That is not okay.",
            subject_id,
        )
        subject_id = new_subject_id
    log.info("Using '%s' as subject_id", subject_id)

    subject_dir = Path(SUBJECTS_DIR / subject_id)
    work_dir = gtk_context.output_dir / subject_id
    if not work_dir.is_symlink():
        work_dir.symlink_to(subject_dir)

    if "subject_id" in command_config:  # this was already handled
        command_config.pop("subject_id")

        pass

    command = generate_command(subject_id, command_config, log)

    return_code = 0

    if len(errors) > 0:
        log.info("Command was NOT run because of previous errors.")
        return_code = 1

    else:

        if not config.get('gear-postprocessing-only'):
            ra_errors, ra_warnings, ra_return_code, metadata = execute_recon_all_command(command, environ, dry_run,
                                                                                         subject_dir, log, metadata)
            errors.extend(ra_errors)
            warnings.extend(ra_warnings)
            return_code = ra_return_code

        if return_code == 0:

            post_errors, post_return_code, metadata = execute_postprocesing_command(config, environ, dry_run,
                                                                                    subject_id, subject_dir, log,
                                                                                    metadata)
            errors.extend(post_errors)
            return_code = post_return_code

    # zip entire output/<subject_id> folder into
    #  <gear_name>_<subject_id>_<analysis.id>.zip
    zip_file_name = (
            gtk_context.manifest["name"]
            + f"_{subject_id}_{gtk_context.destination['id']}.zip"
    )
    if subject_dir.exists():
        log.info("Saving %s in %s as output", subject_id, SUBJECTS_DIR)
        zip_output(str(gtk_context.output_dir), subject_id, zip_file_name)

    else:
        log.error("Could not find %s in %s", subject_id, SUBJECTS_DIR)

    # clean up: remove output that was zipped
    if work_dir.exists():
        log.debug('removing output directory "%s"', str(work_dir))
        work_dir.unlink()
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

    if len(metadata["analysis"]["info"]) > 0:
        with open(f"{gtk_context.output_dir}/.metadata.json", "w") as fff:
            json.dump(metadata, fff)
        log.info(f"Wrote {gtk_context.output_dir}/.metadata.json")
    else:
        log.info("No data available to save in .metadata.json.")
    log.debug(".metadata.json: %s", json.dumps(metadata, indent=4))

    news = "succeeded" if return_code == 0 else "failed"

    log.info("%s is done.  Returning %d", CONTAINER, return_code)

    sys.exit(return_code)


if __name__ == "__main__":
    gear_toolkit_context = flywheel_gear_toolkit.GearToolkitContext()

    main(gear_toolkit_context)
