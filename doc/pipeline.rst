.. _pipeline:


Pipeline Productions
=========================

A pipeline "production" is defined as a single processing of DESI data using a consistent software stack and set of options.  After setting up a production, the pipeline steps are run in order and the status of individual tasks are tracked.  If a task fails, all later processing steps requiring the outputs of that task will also fail.


Processing Steps
------------------------

As a reminder, DESI raw data (real or simulated) is organized by exposures where each exposure has up to 10 spectrographs acquiring data in 3 `bands`.  A single band from a single spectrograph is often referred to as a `frame`.  The pipeline is a chain of processing steps.  A single `step` has one or more individual `tasks`, where a task often operates on a single spectrograph, a single frame, etc.  Here is an overview of the tasks within each step and their inputs / outputs.

#.  **bootcalib** (Optional):  A single bootcalib task depends on all the arcs and flats for a single spectrograph and band for a single night (though it may only use one arc/flat for now).  The output of a bootcalib task is a `psfboot` file for the given night and frame.  This step can be skipped when creating a production.

#.  **specex**:  A single specex task works on one frame and takes a psfboot file and an arc image.  It produces a `psf` file corresponding to the given arc image.

#.  **psfcombine**:  This task takes all psf files for a given night and frame and median combines them into a single `psfnight` file for that frame.

#.  **extract**:  Each of these tasks works on a single frame.  It takes the nightly psf, the image (science or flat), and the fibermap for exposure.  The task outputs a `frame` file.

#.  **fiberflat**:  A fiberflat task takes a frame file from the extraction of a flat and produces a fiberflat file.

#.  **sky**:  This produces a sky model for an extracted science frame using the "most recent" fiberflat file for the given frame.  Each task produces a sky file for the science frame.

#.  **stdstars**:  Each stdstars task works on a single spectrograph.  The inputs are the extracted science frame, the most recent fiberflat, and the sky file for each band in the given spectrograph.  The output is a stdstars file.

#.  **fluxcal**:  Each fluxcal task builds a `calib` file for a given science frame.  The inputs are the extracted science frame, the most recent fiberflat, the sky file, and the stdstars file for corresponding spectrograph.

#.  **procexp**:  These tasks apply the calibration to a specific science frame and produce a `cframe` file.  Inputs are the science frame, the most recent fiberflat, the sky file, and the calib file.

#.  **bricks**:  This step is a single serial task which updates the brick files with the spectra contained in the cframe files.  In the pipeline scripts, this is just a call to a commandline tool.

#.  **zfind**:  This performs the redshift fitting.  Each task works on a single brick and produces a `zbest` file.



Creating a Production
-------------------------

To create a production for some raw data, we use the desi_pipe commandline tool::

    %> desi_pipe --help

.. include:: _static/desi_pipe_help.inc

The most important options are "--raw" which defines the raw data location (default is to use the ${DESI_SPECTRO_DATA} environment variable) and the "--redux" and "--prod" options which together define the location of the production (default is ${DESI_SPECTRO_REDUX}/${SPECPROD}).  When running at NERSC, you **must** use the "--env" option.  The slurm scripts generated by desi_pipe include the contents of the file you provide to this option, and those commands must setup your desi environment from scratch.  Another common option when making small productions for testing is to use "--spectrographs" to restrict the processing to just one (or a few) spectrographs.  Also, for now, I recommend using the "--fakeboot" option to skip the bootcalib step.  Eventually, these bootstrap files will be generated infrequently and reused for multiple nights.

Example
~~~~~~~~~~

Let's assume we have some simulated raw data located in ${SCRATCH}/desi/raw.  We'll also assume that our data reduction directory is ${SCRATCH}/desi/redux.  We'll assume that all of our environment setup discussed in :ref:`install` is done by running a shell function "desi".  We put this command (and any others) into a snippet of text that will be inserted into the pipeline running scripts to initialize our environment::

    %> cat env.sh
    desi

Now we create a production with the first spectrograph.  We also pass in the debug option, which will enable the DEBUG logging level in all pipeline scripts::

    %> desi_pipe --debug \
        --env env.sh \
        --raw ${SCRATCH}/desi/raw \
        --redux ${SCRATCH}/desi/redux \
        --prod smalltest \
        --spectrographs 0

This will create the production directory structure and also make a shell snippet that we can source whenever we want to work with this production::

    %> cd ${SCRATCH}/desi/redux/smalltest
    %> cat setup.sh

    # Generated by desi_pipe
    export DESI_SPECTRO_DATA=/scratch/desi/raw
    export DESI_SPECTRO_REDUX=/scratch/desi/redux
    export PRODNAME=smalltest

    export DESI_LOGLEVEL="DEBUG"

    %> source setup.sh


Updating a Production
--------------------------

Imagine that you created a production and then additional days of data were added to the raw data location.  In order to generate scripts that include this new data, we can simply run desi_pipe again.  First, source the setup file in the production directory::

    $> source setup.sh

Then run desi_pipe with your desired options, but do **not** specify the "--raw", "--redux", or "--prod" options.  The existing production directory will be updated, and future runs of those pipeline scripts will include the new raw data.


Running a Production
-----------------------------

Now that we have used desi_pipe to set up a production, we can optionally modify the global options used for the processing and then submit the pipeline jobs to the queue or run the serial scripts.  From within the production directory, look inside the "run" directory.  Here you will find the `options.yaml` file that contains the global options for all steps of the pipeline.  Edit this file if you want something other than the defaults.  Now look in the "scripts" subdirectory.  This contains two versions of each pipeline script.  One is a slurm batch script which is designed to work at NERSC.  The other is a simple bash script which does the same tasks by calling desi_pipe_run directly.  Note that if you are using a simple cluster with MPI configured, then you can use the --shell_mpi_run and --shell_max_cores options to desi_pipe to configure these generated bash scripts to use MPI directly.

Inside the scripts directory, there are high-level shell scripts named::

    run_{slurm,shell}_{all,<night>}.sh

These scripts are used to run the pipeline on all the data or a specific night, using the slurm scheduler at NERSC or simple bash scripts.


Example
~~~~~~~~~~

Continuing with our NERSC example, let's now go and submit all the pipeline jobs.  There is a helper script which does this job submission and adds dependencies between the jobs so that they run in order.  Go into the run/scripts directory and do::

    ./run_slurm_all.sh

Now you can use the slurm commands to monitor the running state of these jobs, and you can also use the tools described in the next section.


Monitoring a Running Pipeline
-----------------------------------

When desi_pipe is used to create or update a production, it calculates the interdependencies of all data objects for each night.  This dependency graph is called a `plan`, and the nightly plans are written to the "plan" subdirectory inside the production directory.  As the pipeline runs, the state of all objects are updated in memory and at the end of each step, the updated dependency graph (with state information) is dumped to a yaml file.  The initial state is computed by traversing the file system and checking the existence of all files.  Eventually all state information like this will be read/written to a database.

As the pipeline runs, the "run/logs" subdirectory is where log files for all pipeline jobs are written.  The top level directory contains the high-level logs from each pipeline step that is run.  The nightly directories within the logs directory contain the logs from each task.  In the case of slurm jobs, the slurm script output is in a separate log file (named after the job ID), and that file contains the timestamp of the corresponding high-level log file.

Rather than manually searching through log files, it is easy to use the desi_pipe_status commandline tool to query the state of a production.  Before using desi_pipe_status, source the `setup.sh` file in the production directory you want to work with.  Then we can use one of the subcommands::

    %> desi_pipe_status --help

.. include:: _static/desi_pipe_status_help.inc

More help about each of the commands is available by running::

    %> desi_pipe_status <command> --help


Example
~~~~~~~~~~~~~~

Let's say that we have submitted our previous example pipeline and we want to check on its status.  First we make sure that we are working with the correct production::

    %> source ${SCRATCH}/desi/redux/smalltest/setup.sh

To get an overview of all pipeline steps, we do::

    %> desi_pipe_status all

.. include:: _static/desi_pipe_status_all.inc

The color of each step indicates whether it has not started (white), is in-progress (yellow), has succeeded (green), or has failed (red).  The output above indicates that the fiberflat step is in progress and earlier steps have succeeded.  Let's look into the extraction step in more detail::

    %> desi_pipe_status step extract

.. include:: _static/desi_pipe_status_step_extract.inc

Here we see the list of individual tasks run as part of that step, as well as their status (based on the text color).  Let's get more detail about one of the tasks::

    %> desi_pipe_status task XXXXXXX

We can also dump out the log from this task::

    %> desi_pipe_status task XXXXXXX --log


Debugging Failures
-------------------------

look at log


salloc then --retry



