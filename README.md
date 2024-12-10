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

### Print Gene Annotator Description
    # be sure your virtual environment is activated
    # change to project root and run pipeline.py
    $ cd /gene_annotator/
    $ python ./gene_annotator

### Configure to Behave as Executable
You can configure gene_annotator script to behave like a standard Linux utility or system-level executable. This makes your script accessible from the command line just like any other tool installed on your system. You will need administrative privileges so this may not be appropriate in networked environments. 

### Create a symlink to gene_annotate
In /usr/local/bin, which is included in the system's PATH environment variable, create a symlink to the gene_annotate script. This ensures the script is available to all users on the system.

```sh
$ sudo ln -s /path/to/src/gene_annotate /usr/local/bin/gene_annotate
```



## Spin up an instance of the Flask server
TBD

## Use Curl to query annotation data
TBD


# Running with Docker
Here are the steps to build the Gene Annotator container and run it

## Make sure docker is installed
    $ docker --version

## Build the docker image
    # cd to project root and run docker build
    $ cd ../gene_annotator/
    $ docker build -t gene_annotate -f ./containers/gene-annotate-dockerfile .

## Run the container
    # the Dockerfile has an ENTRYPOINT that points to etl/pipeline.py
    # running a container from this image will automatically execute the script
    $ docker run --name gene_annotate_container gene_annotate

## Run Interactively
    # to inspect output files in the container, run unit tests, or the api/app.py
    # run the container interactively and override the ENTRYPOINT
    # map port '5000' of the host to port '5000' of the container
    $ docker run -it -p 5000:5000 --entrypoint /bin/bash --name gene_annotate_container gene_annotate

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

