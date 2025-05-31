#!/bin/bash

# Source the export script to get the paths
source ./helper_scripts/export_python_path.sh

# Replace /Users/arthurvargas/dev/gene_annotator with /opt/pipeline
CONTAINER_PYTHONPATH=${PYTHONPATH//$(pwd)/\/opt\/pipeline}

# Update the Dockerfile
sed -i '' "s|ENV PYTHONPATH=.*|ENV PYTHONPATH=$CONTAINER_PYTHONPATH|" containers/gene-annotation-dockerfile

echo "Updated Dockerfile PYTHONPATH to: $CONTAINER_PYTHONPATH"