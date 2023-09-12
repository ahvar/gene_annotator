# ETL PIPELINE v1.0.0
### A gene and annotation query tool

# Introduction 

This application, ETL PIPELINE, is designed to process gene annotation data. It identifies duplicate entries, logs them, removes them, and performs various data transformation steps. The results are saved in the final_results.csv file.

# Installation and Setup
    
## Extraction: 
Extract all files from the project archive to a location on your filesystem.
## CD to your project root and create a virtual environment with Conda: 
    - this command will create a Python 3.7 venv in your project root, which makes the project more self-contained
    $ conda create --prefix ./envs python=3.7
## Install dependencies:
    - from project root, pip install the requirements
    $ pip install -r requirements.txt
## Configure Python Interpreter (**This step is crucial. Without it, the program will raise an import error as it won't be able to find necessary modules**):
    - from project root, source the export_python_path helper script so the interpreter can properly import modules:
    $ source ./project_root/helper_scripts/export_python_path.sh
## Run the tests
    - change to the test directory and run pytest. It will "discover" tests and run them
    $ cd ./test
    $ pytest -vv

# Usage
From the project root

## Use the helper script to view ETL PIPELINE help message:
 - from project root
$ ./helper_scripts/help.sh

## Run pipeline help directly on CLI
$ python ./etl/pipeline.py --help

## Run pipeline directly:
$ python ./etl/pipelines.py [--etl-output-directory OUTPUT_DIR | -o OUTPUT_DIR] [--debug]

## Or use the helper script:
$ python ./etl/pipeline.py

## Observe the timestamped output directory in etl/
 - check pipeline.log for duplicate and unique record counts

## Spin up an instance of the Flask server
 - change to the api/ directory in project root
 $ ./app

## Use Curl to query annotation data
 $ curl "http://localhost:5000/genes?gene_stable_id=ENSG00000281775&pid_suffix=SF0"



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

