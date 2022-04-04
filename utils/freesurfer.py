"""Install Freesurfer license.txt file where algorithm expects it.
"""

import json
import logging
import re
import shutil
from pathlib import Path

log = logging.getLogger(__name__)


def install_freesurfer_license(
    input_license_path, freesurfer_license_string, fw, destination_id, fs_license_path,
):
    """Install the Freesurfer license file.

    The file is written at the provided path.  License text is found in one of
    3 ways and in this order:

    1) license.txt is provided as an input file,
    2) the text from license.txt is pasted into the "gear-FREESURFER_LICENSE"
       config, or
    3) the text from license.txt is pasted into a Flywheel project's "info"
       metadata.

    See `How to include a Freesurfer license file...
    <https://docs.flywheel.io/hc/en-us/articles/360013235453>`_

    Args:
        input_license_path (str) path to license file supplied by user as an input file
        freesurfer_license_string (str) text of Freesurfer license file (space separated)
        fw (flywheel.client.Client) Flywheel SDK client
        destination_id (str): ID of the destination of the analysis
        fs_license_path (str): Path to where the license should be installed,
            $FREESURFER_HOME, usually "/opt/freesurfer/license.txt".

    Example:
        >>> from freesurfer import install_freesurfer_license
        >>> install_freesurfer_license(None, None, gtk_context.client, "5f8748421193aed33c35f172" , '/opt/freesurfer/license.txt')
    """

    log.debug("Looking for Freesurfer license")

    license_info = ""

    # 1) Check if the required FreeSurfer license file has been provided
    # as an input file.

    if input_license_path:  # just copy the file to the right place

        log.info("FreeSurfer license path is %s", input_license_path)
        fs_path_only = Path(fs_license_path).parents[0]
        fs_file = Path(fs_license_path).name

        if fs_file != "license.txt":
            log.warning(
                "Freesurfer license file is usually license.txt, not " "%s",
                fs_license_path,
            )

        if not Path(fs_path_only).exists():
            Path(fs_path_only).mkdir(parents=True)
            log.warning("Had to make freesurfer license path: %s", fs_license_path)

        shutil.copy(input_license_path, fs_license_path)

        license_info = "copied input file"
        log.info("Using FreeSurfer license in input file.")

    # 2) see if the license info was passed as a string argument
    elif freesurfer_license_string:
        license_info = re.sub(r"(\S){1} ", "\1\n", freesurfer_license_string)

        log.info("Using FreeSurfer license in gear argument.")

    # 3) see if the license info is in the project's info
    else:

        project_id = fw.get_analysis(destination_id)["parents"]["project"]
        project = fw.get_project(project_id)

        if "FREESURFER_LICENSE" in project["info"]:
            space_separated_text = project["info"]["FREESURFER_LICENSE"]
            license_info = "\n".join(space_separated_text.split())

            log.info("Using FreeSurfer license in project info.")

    # If it was passed as a string or was found in info, license_info is
    # set so save the Freesurfer license as a file in the right place.
    # If the license was an input file, it was copied to the right place
    # above (case 1).
    if license_info == "copied input file":
        pass  # all is well

    elif license_info != "":

        head = Path(fs_license_path).parents[0]

        if not Path(head).exists():
            Path(head).mkdir(parents=True)
            log.debug("Created directory %s", head)

        with open(fs_license_path, "w") as flp:
            flp.write(license_info)
            # log.debug("Wrote license %s", license_info)
            log.debug("Wrote license file %s", fs_license_path)

    else:
        msg = "Could not find FreeSurfer license anywhere"
        raise FileNotFoundError(f"{msg} ({fs_license_path}).")
