FROM freesurfer/freesurfer:7.1.1 as base

LABEL maintainer="support@flywheel.io"

RUN (curl -sL https://rpm.nodesource.com/setup_12.x | bash -) \
  && yum clean all -y \
  && yum update -y \
  && yum install -y zip unzip nodejs tree libXt libXext ncurses-compat-libs \
  && yum clean all -y \
  && npm install npm --global

RUN source $FREESURFER_HOME/SetUpFreeSurfer.sh

# Extra segmentations require matlab compiled runtime
RUN fs_install_mcr R2014b

# Fix known race condition bug introduced in 7.1.1
# https://www.mail-archive.com/freesurfer@nmr.mgh.harvard.edu/msg68263.html
# RUN sed -i.bak '4217 s/^/#/' $FREESURFER_HOME/bin/recon-all
# The above line is already in patched recon-all along with 2nd -parallel fix
# https://www.mail-archive.com/freesurfer@nmr.mgh.harvard.edu/msg68878.html
RUN mv $FREESURFER_HOME/bin/recon-all $FREESURFER_HOME/bin/recon-all.bak
COPY patch/recon-all $FREESURFER_HOME/bin/recon-all

# Fix known bug by swapping in updated script
# See https://surfer.nmr.mgh.harvard.edu/fswiki/ThalamicNuclei
RUN mv $FREESURFER_HOME/bin/quantifyThalamicNuclei.sh $FREESURFER_HOME/bin/quantifyThalamicNuclei.sh.bak
COPY patch/quantifyThalamicNuclei.sh $FREESURFER_HOME/bin/quantifyThalamicNuclei.sh

# Save environment so it can be passed in when running recon-all.
ENV PYTHONUNBUFFERED 1
RUN python -c 'import os, json; f = open("/tmp/gear_environ.json", "w"); json.dump(dict(os.environ), f)'

# Install a version of python to run Flywheel code and keep it separate from the
# python that Freesurfer uses.  Saving the environment above makes sure it is not
# changed in the Flyfwheel environment.

# Set CPATH for packages relying on compiled libs (e.g. indexed_gzip)
ENV PATH="/root/miniconda3/bin:$PATH" \
    CPATH="/root/miniconda3/include/:$CPATH" \
    LANG="C.UTF-8" \
    PYTHONNOUSERSITE=1

RUN wget \
    https://repo.anaconda.com/miniconda/Miniconda3-py38_4.8.3-Linux-x86_64.sh \
    && mkdir /root/.conda \
    && bash Miniconda3-py38_4.8.3-Linux-x86_64.sh -b \
    && rm -f Miniconda3-py38_4.8.3-Linux-x86_64.sh

# Installing precomputed python packages
RUN conda install -y python=3.8.5 && \
    chmod -R a+rX /root/miniconda3; sync && \
    chmod +x /root/miniconda3/bin/*; sync && \
    conda build purge-all; sync && \
    conda clean -tipsy && sync

COPY requirements.txt /tmp
RUN pip install -r /tmp/requirements.txt && \
    rm -rf /root/.cache/pip

# Make directory for flywheel spec (v0)
ENV FLYWHEEL /flywheel/v0
WORKDIR ${FLYWHEEL}

# Copy executable/manifest to Gear
COPY manifest.json ${FLYWHEEL}/manifest.json
COPY utils ${FLYWHEEL}/utils
COPY run.py ${FLYWHEEL}/run.py

# Configure entrypoint
RUN chmod a+x ${FLYWHEEL}/run.py
ENTRYPOINT ["/flywheel/v0/run.py"]
