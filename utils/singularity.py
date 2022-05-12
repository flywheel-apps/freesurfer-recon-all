"""Do what it takes to be able to run gears in Singularity.
"""

import logging
import os
import re
import tempfile
from pathlib import Path
from glob import glob

log = logging.getLogger(__name__)


FWV0 = "/flywheel/v0"
SCRATCH_NAME = "gear-temp-dir-"


def log_singularity_details():
    """Help debug Singularity settings, including permissions and UID."""
    log.info(f"SINGULARITY_NAME is {os.environ['SINGULARITY_NAME']}")
    log.debug(f"UID is {os.getuid()}")
    log.debug("Permissions: 4=read, 2=write, 1=read")
    locs = glob("/tmp/*") + glob("/flywheel/v0/*") + glob("/home/bidsapp")
    for loc in locs:
        for prmsn in [os.R_OK, os.W_OK, os.X_OK]:
            log.debug(f"Permission {prmsn} for {loc}: {os.access(loc,prmsn)}")
        if ("gear_environ" in loc) and not os.access(loc, os.R_OK):
            log.error(
                "Cannot read gear_environ.json. Gear will download BIDS in the wrong spot and will not wrap up properly."
            )

def run_in_tmp_dir():
    """Copy gear to a temporary directory and cd to there.

    Returns:
        tmp_path (path) The path to the temporary directory so it can be deleted
    """

    running_in = ""

    # This just logs some info.  Leaving it here in case it might be useful.
    if "SINGULARITY_NAME" in os.environ:
        running_in = "Singularity"
        # log.debug("SINGULARITY_NAME is %s", os.environ["SINGULARITY_NAME"])
        log_singularity_details()

    else:
        cgroup = Path("/proc/self/cgroup")
        if cgroup.exists():
            with open("/proc/self/cgroup") as fp:
                for line in fp:
                    if re.search("/docker/", line):
                        running_in = "Docker"
                        break

    if running_in == "":
        log.debug("NOT running in Docker or Singularity")
    else:
        log.debug("Running in %s", running_in)

    # This used to remove any previous runs (possibly left over from previous testing) but that would be bad
    # if other bids-fmripreps are running on shared hardware at the same time because their directories would
    # be deleted mid-run.  A very confusing error to debug!

    # Create temporary place to run gear
    WD = tempfile.mkdtemp(prefix=SCRATCH_NAME, dir="/tmp")
    log.debug("Gear scratch directory is %s", WD)

    new_FWV0 = Path(WD + FWV0)
    new_FWV0.mkdir(parents=True)
    abs_path = Path(".").resolve()
    names = list(Path(FWV0).glob("*"))
    for name in names:
        if name.name == "gear_environ.json":  # always use real one, not dev
            (new_FWV0 / name.name).symlink_to(Path(FWV0) / name.name)
        else:
            (new_FWV0 / name.name).symlink_to(abs_path / name.name)
    os.chdir(new_FWV0)  # run in /tmp/... directory so it is writeable
    log.debug("cwd is %s", Path.cwd())

    return new_FWV0
