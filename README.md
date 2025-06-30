# Gene Annotator v1.0.0

# Introduction
ETL pipeline and microblog

# Key Features
- Data processing pipeline
- Collaboration network with microblogging capabilities and researcher profiles
- Pipeline run history and sharing
- Full text search for posts

# Access
You can access the development instance of Gene Annotator at:
[Gene Annotator Development Instance](http://gene-annotator-lb-1630757355.us-east-1.elb.amazonaws.com:8000/auth/login?next=%2F)

This instance provides a fully functional environment with:
- Sample gene and annotation data
- Test user accounts (see below for credentials)
- Full pipeline functionality
- Elasticsearch integration for post searching

### Test Credentials
You can log in with any of these accounts to explore the application:
- Username: `test-user` / Password: `password123`
- Username: `alice_admin` / Password: `alicepw123`
- Username: `arthurvargas` / Password: `(contact admin for password)`

# Data Processing Steps
- Reads gene and annotation data from file, loads to sql db
- Identifies and logs duplicate records
- Removes duplicate records and logs the unique ones
- Writes the gene_type count to file
- Determines if hgnc_id exists and appends a new column hgnc_id_exists
- Merges gene and annotation datasets
- Excludes records where tigrfam_id is null or contains specific undesired values
- Writes excluded tigrfam_id entries to excluded_tigrfam_ids.csv
- Stores results as PipelineRun in db and writes to a final_results file

# Application Architecture
- Flask Web App
- SQLAlchemy ORM: DB interaction layer
- Elasticsearch: Full-text search for researcher posts
- Alembic: Database migrations
- Pandas: File I/O and data processing steps
- Typer CLI

# Data Models
- Gene, GeneAnnotation, Researcher, Post, PipeineRun

# How to Run Gene Annotator Locally
Here are the steps to run Gene Annotator CLI locally. 
    
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
## Configure your interpreter's PYTHONPATH
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

## Running the Flask Application Locally

### 1. Set Up the Database
After activating your virtual environment, initialize and create the database:

```sh
flask db init
flask db migrate -m "initial migration"
flask db upgrade
```

#### Run dev server
```sh
flask run
```
By default, the server will run on: http://127.0.0.1:5000
Login with your credentials or register as a new user.

#### View Datasets
View the Gene and Gene Annotation Datasets

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

