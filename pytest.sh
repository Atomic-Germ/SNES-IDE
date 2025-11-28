#!/usr/bin/env bash
# activate venv
source .venv/bin/activate

# format imports and code 
isort src tests
black src tests

# run tests
pytest -q

# run pylint
pylint src tests