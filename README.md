# freesurfer7
Gear that runs FreeSurfer version 7.1.0 release May 11, 2020

This gear was created using the [bdis-app-template](https://github.com/flywheel-apps/bids-app-template).  For documentation on how to run the tests in this gear, please see that README file.

# Inputs
### bidsignore (optional)
A list of patterns (like .gitignore syntax) defining files that should be ignored by the 
bids validator.

### freesurfer_license (optional)
Your FreeSurfer license file. [Obtaining a license is free](https://surfer.nmr.mgh.harvard.edu/registration.html).
This file will by copied into the $FSHOME directory.  There are [three ways](https://docs.flywheel.io/hc/en-us/articles/360013235453-How-to-include-a-Freesurfer-license-file-in-order-to-run-the-fMRIPrep-gear-)
to provide the license to this gear.  A license is required for this gear to run.

# Configuration Options
Note: arguments that start with "gear-" are not passed to the BIDS App.

### n_cpus (optional)
Number of CPUs/cores use.  The default is all available.

### verbose (optional)
Verbosity argument passed to the BIDS App.

### gear-run-bids-validation (optional)
Gear argument: Run bids-validator after downloading BIDS formatted data.  Default is true.

### gear-ignore-bids-errors (optional)
Gear argument: Run BIDS App even if BIDS errors are detected when gear runs bids-validator.

### gear-log-level (optional)
Gear argument: Gear Log verbosity level (ERROR|WARNING|INFO|DEBUG)

### gear-save-intermediate-output (optional)
Gear argument: The BIDS App is run in a "work/" directory.  Setting this will save ALL 
contents of that directory including downloaded BIDS data.  The file will be named
"<BIDS App>_work_<run label>_<analysis id>.zip"

### gear-intermediate-files (optional)
Gear argument: A space separated list of FILES to retain from the intermediate work 
directory.  Files are saved into "<BIDS App>_work_selected_<run label>_<analysis id>.zip"

### gear-intermediate-folders (optional)
Gear argument: A space separated list of FOLDERS to retain from the intermediate work 
directory.  Files are saved into "<BIDS App>_work_selected_<run label>_<analysis id>.zip"

### gear-dry-run (optional)
Gear argument: Do everything except actually executing the BIDS App.

### gear-keep-output (optional)
Gear argument: Don't delete output.  Output is always zipped into a single file for 
easy download.  Choose this option to prevent output deletion after zipping.

### gear-FREESURFER_LICENSE (optional)
Gear argument: Text from license file generated during FreeSurfer registration. 
Copy the contents of the license file and paste it into this argument.

# Workflow
This gear runs a short bash script that helps test the functionality of this 
bids-app-teamplate.

# Outputs
This gear produces some silly output that is not important just to prove that it can.
