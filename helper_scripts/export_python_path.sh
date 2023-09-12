#!/bin/bash

# run this script to set PYTHONPATH of the python interpreter in your virtual environment

# Get the helper script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# cd from the 'helper_scripts' dir one level up to get the project root
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Construct PYTHONPATH dynamically based on the project root
export PYTHONPATH="$PROJECT_ROOT:$PROJECT_ROOT/etl:$PROJECT_ROOT/utils:$PROJECT_ROOT/etl/data:$PROJECT_ROOT/test:$PROJECT_ROOT/test/utils"

echo "PYTHONPATH set to: $PYTHONPATH"
