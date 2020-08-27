"""Given string, return something safe to use as a file name."""

import logging
import re

log = logging.getLogger(__name__)


def make_file_name_safe(input_basename, replace_str=""):
    """Remove non-safe characters from a filename and return a filename with
        these characters replaced with replace_str.

    :param input_basename: the input basename of the file to be replaced
    :type input_basename: str
    :param replace_str: the string with which to replace the unsafe characters
    :type   replace_str: str
    :return: output_basename, a safe
    :rtype: str
    """

    safe_patt = re.compile(r"[^A-Za-z0-9_\-.]+")
    # if the replacement is not a string or not safe, set replace_str to x
    if not isinstance(replace_str, str) or safe_patt.match(replace_str):
        log.warning("{} is not a safe string, removing instead".format(replace_str))
        replace_str = ""

    # Replace non-alphanumeric (or underscore) characters with replace_str
    safe_output_basename = re.sub(safe_patt, replace_str, input_basename)

    if safe_output_basename.startswith("."):
        safe_output_basename = safe_output_basename[1:]

    log.debug('"' + input_basename + '" -> "' + safe_output_basename + '"')

    return safe_output_basename
