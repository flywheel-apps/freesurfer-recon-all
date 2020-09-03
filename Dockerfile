FROM freesurfer/freesurfer:7.1.1 as base

LABEL maintainer="support@flywheel.io"

RUN (curl -sL https://rpm.nodesource.com/setup_12.x | bash -) \
  && yum clean all -y \
  && yum update -y \
  && yum install -y zip nodejs tree \
  && yum clean all -y \
  && npm install npm --global

RUN npm install -g bids-validator@1.5.4

RUN source $FREESURFER_HOME/SetUpFreeSurfer.sh

# Save docker environ
ENV PYTHONUNBUFFERED 1
RUN python -c 'import os, json; f = open("/tmp/gear_environ.json", "w"); json.dump(dict(os.environ), f)'

# Set CPATH for packages relying on compiled libs (e.g. indexed_gzip)
ENV PATH="/root/miniconda3/bin:$PATH" \
    CPATH="/root/miniconda3/include/:$CPATH" \
    LANG="C.UTF-8" \
    PYTHONNOUSERSITE=1

# Get a new version of python that can run flywheel
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
