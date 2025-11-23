#!/bin/bash
# Run all quality checks

set -e

echo "================================"
echo "Running Code Quality Checks"
echo "================================"
echo ""

# Run formatting check
./scripts/lint.sh

echo ""
echo "================================"
echo "Running Type Checks"
echo "================================"
echo ""

# Run type checking
./scripts/type-check.sh

echo ""
echo "================================"
echo "Running Tests"
echo "================================"
echo ""

# Run tests
cd backend && uv run pytest

echo ""
echo "================================"
echo "✓ All quality checks passed!"
echo "================================"
