#!/bin/bash

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
export PYTHONPATH="$PROJECT_ROOT:$PROJECT_ROOT/etl:$PROJECT_ROOT/utils:$PROJECT_ROOT/etl/data:$PROJECT_ROOT/test:$PROJECT_ROOT/test/utils"

echo -----------------------------------------------------------------------
echo python path:
echo "PYTHONPATH set to: $PYTHONPATH"
echo -----------------------------------------------------------------------

echo -----------------------------------------------------------------------
echo etl pipeline help message...
echo -----------------------------------------------------------------------
echo

python ./etl/pipeline.py --help







