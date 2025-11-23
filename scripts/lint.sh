#!/bin/bash
# Run linting checks

set -e

echo "Running black check..."
uv run black --check backend/ main.py

echo "Running isort check..."
uv run isort --check-only backend/ main.py

echo "Running flake8..."
uv run flake8 backend/ main.py

echo "✓ All linting checks passed!"
