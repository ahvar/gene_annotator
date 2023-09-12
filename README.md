# ETL PIPELINE v1.0.0
### A gene and annotation query tool

# Introduction 

This application, ETL PIPELINE, is designed to process gene annotation data. It identifies duplicate entries, logs them, removes them, and performs various data transformation steps. The results are saved in the final_results.csv file.

# Functionality
     - Reads data from genes.csv and gene_annotations.tsv.
     - Identifies and logs duplicate records.
     - Removes duplicate records and logs the unique ones.
     - Writes the gene_type count to gene_type_count.csv.
     - Determines if hgnc_id exists and appends a new column hgnc_id_exists.
     - Merges gene data with gene annotations.
     - Excludes records where tigrfam_id is null or contains specific undesired values.
     - Writes excluded tigrfam_id entries to excluded_tigrfam_ids.csv.
     - Outputs the final merged data to final_results.csv.

# Installation and Setup
    1. Extraction: Extract all files from the project archive to a location on your filesystem.
    2. CD to your project root and create a virtual environment with Conda: 
        $ conda create --prefix ./envs python=3.7
    3. Install dependencies:
        $ pip install -r requirements.txt
    4. Configure Python Interpreter (**this step is crucial. without it, the program will raise an import error as it won't be able to find necessary modules**):
        - Source the script to configure the Python interpreter:
        $ source ./project_root/scripts/export_python_path.sh

# Usage
From the project root

## View the help message:
$ python ./etl/pipeline.py --help

## Run the application with the following command:
$ ./etl/pipelines.py [--etl-output-directory OUTPUT_DIR | -o OUTPUT_DIR] [--debug]



    


Each command is detailed below:

## from-internal-table
Operates on an existing internal QC table containing sample results for a Genexus sequencer plan.

#### Preconditions:
An internal QC table has been previously generated. The QC table accurately includes the corresponding client
and project IDs for each sample.

#### Operation: 
Utilizes client and project data to create subdirectories, named after the respective client and project IDs.

#### Usage: 
Typically invoked when IonQC cannot authenticate to the Clarity database, due to geographical limitations or unexpected
data retrieval errors. In such cases, a user would first generate an internal QC table with preview-internal-table, manually
enter the necessary client and project data, and execute from-internal-table, passing the updated internal QC table as an argument.


## preview-internal-table
Generates an internal QC table that outputs to the standard output (stdout) and/or a specified file, providing an overview
of the plan data and highlighting unexpected or missing QC metrics.

#### Functionality:
Primarily designed for data preview; does not perform post-processing actions like file copying or renaming.

#### Special Use Cases:
Supports execution with a JSON-formatted data file, mainly for testing purposes.

## copy-rename-report
Manages QC metrics for a specified plan on an active Genexus sequencer. The user must pass the target plan name as an argument.

#### Execution:
Retrieves, loads, and deserializes QC metrics from the Genexus API v6.6. The metrics are organized into the internal QC table and the QC summary.

#### Internal QC Table:
The internal QC table contains all available QC metrics. Unavailable metrics are denoted as "unavailable".

#### QC Summary:
Presents an abbreviated version of the internal QC table. Both tables list only the samples corresponding to a particular
client ID and project, representing a subset of all plan samples.

#### Post-Processing:
Locates the directory containing output files synced from the sequencer to network storage, and duplicates BAM, FASTQ, and VCF
files to their respective client/project/timestamp directories for organization.

# Getting Started
## Login to vsd (or "the DEE"), using Putty or enter the command
   $ ssh vsd-login01.eacc.ds.quintiles.com
 
## Select the working data for your run
   $ ls /mounts/working-data | grep -i ion
   ion-qc-r1-dev
   ion-qc-test
   IonQC-uat-HD
   tso500Comp-SVT_automation-test
 
## Setup dee with your chosen data
   $ setup-dee-env --working_data=ion-qc-dev
 
## Now, you can run the thing, let's start by just asking for the usage statement
   $ ea-dc-runner --pty -i q2gn-ion-qc:<tag>-<build> ionqc --help
   ea-dc-runner log: /opt/ea/log/dc-runner/q2gn-ion-qc_develop-106322-20230118-175700-729726270/ea-dc-runner.log
   TraceId: 6ad5894a-9783-11ed-b3e2-005056a0db44
   Usage: torrent_driver.py [OPTIONS] COMMAND [ARGS]...
 
   Options:
   --help  Show this message and exit.
   
   Commands:
   copy-rename-report         Runs QC checks on sequencer outputs for an Ion...
   preview-internal-table     Writes an internal QC table to stdout or an...
   from-samplesheet           Performs copy-rename on samples in the samplesheet...

# Build and Test
TBD

# Contribute
You must be able to explain each line of code you contribute to a rubber duck; or some other odd, uninspiring, inanimate object.

