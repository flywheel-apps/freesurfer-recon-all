#!/usr/bin/env python3
"""Determine level at which the gear is running."""

import logging

from flywheel import ApiException

log = logging.getLogger(__name__)


def get_run_level_and_hierarchy(fw, destination_id):
    """Determine the level at which a job is running, given a destination

    Args:
        fw (gear_toolkit.GearToolkitContext.client): flywheel client
        destination_id (id): id of the destination of the gear

    Returns:
        hierarchy (dict): containing the run_level and labels for the
            run_label, group, project, subject, session, and
            acquisition.

    Note:
        This returns "no_parent" for run_level when the destination has no
        parent and returns run_level of "no_destination" if the destination
        has no "parents" attribute.  In both of these cases, if the job's
        destination.type is "acquisition" then the job is likely a utility
        gear running on an acquisition.
        This function is meant to be run by analysis gears.
    """

    try:
        destination = fw.get(destination_id)

        parent = destination.get("parent", None)
        if parent:
            run_level = destination.parent.type
        else:
            run_level = "no_parent"
        log.info("run_level = %s", run_level)

        group = destination.parents["group"]
        log.info("group = %s", group)

        if destination.parents["project"]:
            project = fw.get(destination.parents["project"])
            project_label = project.label
        else:
            project_label = "unknown project"
        log.info("project_label = %s", project_label)

        if destination.parents["subject"]:
            subject = fw.get(destination.parents["subject"])
            # subject_code = subject.code
            subject_label = subject.label
            # subject_master_code = subject.master_code
            # subject_firstname = subject.firstname
            # subject_lastname = subject.lastname
        else:
            subject_label = "unknown subject"
        log.info("subject_label = %s", subject_label)

        if destination.parents["session"]:
            session = fw.get(destination.parents["session"])
            session_label = session.label
        else:
            session_label = "unknown session"
        log.info("session_label = %s", session_label)

        if destination.parents["acquisition"]:
            acquisition = fw.get(destination.parents["acquisition"])
            acquisition_label = acquisition.label
        else:
            acquisition_label = "unknown acquisition"
        log.info("acquisition_label = %s", acquisition_label)

        if run_level == "project":
            run_label = project_label
        elif run_level == "subject":
            run_label = subject_label
        elif run_level == "session":
            run_label = session_label
        elif run_level == "acquisition":
            run_label = acquisition_label
        elif run_level == "no_parent":
            run_label = "unknown"

    except ApiException as err:
        logging.exception("Unable to get level and hierarchy")
        run_level = "no_destination"
        run_label = "unknown"
        group = None
        project_label = None
        subject_label = None
        session_label = None
        acquisition_label = None

    hierarchy = {
        "run_level": run_level,
        "run_label": run_label,
        "group": group,
        "project_label": project_label,
        "subject_label": subject_label,
        "session_label": session_label,
        "acquisition_label": acquisition_label,
    }

    return hierarchy
