#!/usr/bin/env bash
set -euo pipefail
source .venv/bin/activate
isort src tests
black src tests