#!/usr/bin/env bash
source .venv/bin/activate
python -m pip install --upgrade build
python -m build
python -m pip install --force-reinstall dist/*.whl