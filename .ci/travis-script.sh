#!/bin/bash

set -ev

BASE_CMD="docker-compose -f .travis.compose.yml run --rm test-hbmpc"

if [ "${BUILD}" == "tests" ]; then
    $BASE_CMD pytest -v \
        --cov=honeybadgermpc \
        --cov-report=term-missing \
        --cov-report=xml \
        --profile
    $BASE_CMD python tests/print_profiler_data.py
elif [ "${BUILD}" == "flake8" ]; then
    flake8
elif [ "${BUILD}" == "docs" ]; then
    $BASE_CMD sphinx-build -M html docs docs/_build -c docs -W
fi
