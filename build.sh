#!/usr/bin/env bash
set -euo pipefail
source .venv/bin/activate
python -m build
python -m pip install --force-reinstall dist/*.whl