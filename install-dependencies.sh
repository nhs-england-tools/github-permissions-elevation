#!/bin/bash

set -e

# Set the base directory
BASE_DIR="$(pwd)"
SRC_DIR="${BASE_DIR}/src"

install_dependencies() {
    local lambda_dir=$1
    local lambda_name=$(basename $lambda_dir)
    
    echo "Installing dependencies for ${lambda_name}..."
    pip install -r ${lambda_dir}/test_requirements.txt
    echo "Dependencies installed successfully for ${lambda_name}."
}

# Install dependencies for all lambdas
cd ${SRC_DIR}
python3.12 -m venv env
source env/bin/activate
python3.12 -m pip install --upgrade pip
for lambda_dir in ${SRC_DIR}/*/; do
    if [[ "$lambda_dir" != *"env"* ]]; then
        install_dependencies $lambda_dir
    fi
done
deactivate