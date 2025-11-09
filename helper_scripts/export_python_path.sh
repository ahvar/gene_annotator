#!/bin/bash

# run this script to set PYTHONPATH of the python interpreter in your virtual environment

# Get the helper script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# cd from the 'helper_scripts' dir one level up to get the project root
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Construct PYTHONPATH dynamically based on the project root
# Only including directories that actually exist in your project
export PYTHONPATH="$PROJECT_ROOT:$PROJECT_ROOT/src:$PROJECT_ROOT/src/app:$PROJECT_ROOT/src/app/models:$PROJECT_ROOT/src/app/main:$PROJECT_ROOT/src/app/auth:$PROJECT_ROOT/src/app/errors:$PROJECT_ROOT/src/utils:$PROJECT_ROOT/test:$PROJECT_ROOT/test/utils:$PROJECT_ROOT/test/app:$PROJECT_ROOT/test/app/models:$PROJECT_ROOT/migrations"

echo "PYTHONPATH set to: $PYTHONPATH"
echo ""
echo "Available custom modules:"
echo "  - src.app (Flask application)"
echo "  - src.app.models (Database models)"
echo "  - src.app.main (Main blueprint routes)"
echo "  - src.app.auth (Authentication blueprint)"
echo "  - src.utils (Pipeline utilities)"
echo "  - test.app (Test application modules)"
echo "  - test.app.models (Test model modules)"
echo "  - test.utils (Test utilities)"