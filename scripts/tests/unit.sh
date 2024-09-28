#!/bin/bash

set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

# This file is for you! Edit it to call your unit test suite. Note that the same
# file will be called if you run it locally as if you run it on CI.

# Replace the following line with something like:
#
#   rails test:unit
#   python manage.py test
#   npm run test
#
# or whatever is appropriate to your project. You should *only* run your fast
# tests from here. If you want to run other test suites, see the predefined
# tasks in scripts/test.mk.

BASE_DIR="$(pwd)"
SRC_DIR="${BASE_DIR}/src"
cd ${SRC_DIR}
source env/bin/activate
coverage_files=()
for lambda_dir in ${SRC_DIR}/*/; do
    if [[ "$lambda_dir" != *"env"* ]]; then
        echo "Running unit tests for ${lambda_dir}..."
        pushd $lambda_dir > /dev/null
        python -m coverage run --source=. -m pytest

        cp .coverage ../.coverage.$(basename $lambda_dir)
        coverage_files+=(".coverage.$(basename $lambda_dir)")
        popd > /dev/null
    fi
done

if [ ${#coverage_files[@]} -ne 0 ]; then
    echo "Combining coverage files..."
    python -m coverage combine "${coverage_files[@]}"
    python -m coverage html
    python -m coverage xml -o coverage.xml
    echo "Removing individual coverage files..."
    rm "${coverage_files[@]}"
else
    echo "No coverage files found."
fi
deactivate
