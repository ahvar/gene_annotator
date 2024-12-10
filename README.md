# Gene Annotator v0.1.0
### A gene annotation, query, and QC tool

# Introduction 
Annotate genomic data

# Run Gene Annotator Locally
Here are the steps to run Gene Annotator from the command-line in your local environment. 
    
## Extraction: 
Extract or clone all files to your local environment.
## CD to your project root and create a virtual environment: 
    # create a Python 3.12 venv in your project root
    # conda is used in this example
    $ cd ../path/to/project-root
    $ conda create --prefix ./envs python=3.12
## Activate your virtual environment
    # from the project root
    $ conda activate ./envs
## Install dependencies:
    # pip install dependencies defined
    $ pip install -r requirements.txt
## Modify PYTHONPATH for the interpreter in your virtual environment
    # from project root, source the export_python_path helper script 
    $ source ./gene_annotator/helper_scripts/export_python_path.sh
## Run the tests
    # change to the test directory and run pytest.
    $ cd test/
    $ pytest -vv

# Usage

## Print the help message
Here are two options for printing the help message for Gene Annotator

### Option 1: Gene Annotator help message locally
    # be sure your virtual environment is activated
    # change to project root and run pipeline.py
    $ cd/gene_annotator/
    $ python ./gene_annotator

## Run the Gene Annotator
Here are two options for running the pipeline

### Option 1: Run Gene Annotator
    # be sure your virtual environment is activated
    # change to project root and run pipeline.py
    $ cd/gene_annotator/
    $ python ./etl/pipeline.py

### Option 2: Run Gene Annotator using helper script
    # be sure your virtual environment is activated
    # change to project root and run the helper script
    $ cd/gene_annotator/
    $ python ./helper_scripts/run_etl.sh

Now you can observe the timestamped output directory in etl/ and check the/gene_annotator/etl/output_<timestamp>/logs/pipeline.log for duplicate and unique record counts

## Spin up an instance of the Flask server
    # change to the api/ directory in project root and run the app
    $ cd ./gene_annotator/api
    $ ./app.py

## Use Curl to query annotation data
 $ curl "http://localhost:5000/genes?gene_stable_id=ENSG00000281775&pid_suffix=SF0"


# Running with Docker
Here are the steps to build the Gene Annotator container and run it

## Make sure docker is installed
    $ docker --version

## Build the docker image
    # cd to project root and run docker build
    $ cd ../gene_annotator/
    $ docker build -t etl-pipeline -f ./containers/etl-pipeline-dockerfile .

## Run the container
    # the Dockerfile has an ENTRYPOINT that points to etl/pipeline.py
    # running a container from this image will automatically execute the script
    $ docker run --name etl_pipeline_container etl-pipeline

## Run Interactively
    # to inspect output files in the container, run unit tests, or the api/app.py
    # run the container interactively and override the ENTRYPOINT
    # map port '5000' of the host to port '5000' of the container
    $ docker run -it -p 5000:5000 --entrypoint /bin/bash --name etl_pipeline_container etl-pipeline


Now, if ./api/app.py is run inside the container, you should be able to access the service from
your machine's browser or using a curl command from the terminal


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

