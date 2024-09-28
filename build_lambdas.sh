#!/bin/bash

set -e

# Set the base directory
BASE_DIR="$(pwd)"
SRC_DIR="${BASE_DIR}/src"
TERRAFORM_DIR="${BASE_DIR}/infrastructure/tf_generated"

# Function to build a lambda
build_lambda() {
    local lambda_dir=$1
    local lambda_name=$(basename $lambda_dir)
    
    echo "Building ${lambda_name}..."
    BUILD_DIR=$(mktemp -d)
    
    cp -R ${lambda_dir}/* ${BUILD_DIR}/
    mkdir -p ${BUILD_DIR}/common
    cp -R ${SRC_DIR}/common/* ${BUILD_DIR}/common/
    
    cat ${BUILD_DIR}/requirements.txt ${SRC_DIR}/common/requirements.txt > ${BUILD_DIR}/combined_requirements.txt
    
    pip install --platform manylinux2014_x86_64 --implementation cp --only-binary=:all: --target ${BUILD_DIR} -r ${BUILD_DIR}/combined_requirements.txt
    
    rm -rf ${BUILD_DIR}/tests ${BUILD_DIR}/*requirements.txt
    (cd ${BUILD_DIR} && zip -r ${TERRAFORM_DIR}/${lambda_name}.zip .)
    
    rm -rf ${BUILD_DIR}
    
    echo "${lambda_name} built successfully."
}

# Build all lambdas
for lambda_dir in ${SRC_DIR}/*/; do
    if [[ "$lambda_dir" != *"common"* ]]; then
        build_lambda $lambda_dir
    fi
done

echo "All lambdas built successfully."