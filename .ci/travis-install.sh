#!/bin/bash

pip install --upgrade pip

if [ "${BUILD}" == "tests" ]; then
    pip install --upgrade codecov
    docker-compose -f .travis.compose.yml build --no-cache test-hbmpc
    #apt-get -y install libgmp-dev
    #pip install --no-cache-dir -e .[test]
elif [ "${BUILD}" == "flake8" ]; then
    pip install --upgrade flake8
elif [ "${BUILD}" == "docs" ]; then
    pip install --no-cache-dir -e .[docs]
fi
