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



    

# Contribute
You must be able to explain each line of code you contribute to a rubber duck; or some other odd, uninspiring, inanimate object.

