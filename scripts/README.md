# Development Scripts

This directory contains scripts for maintaining code quality in the RAG chatbot project.

## Available Scripts

### `format.sh`
Automatically formats all Python code in the project using black and isort.

```bash
./scripts/format.sh
```

This will:
- Sort imports with isort (compatible with black)
- Format code with black (88 character line length)

### `lint.sh`
Checks code formatting and style without making changes.

```bash
./scripts/lint.sh
```

This runs:
- black --check (ensures code is formatted)
- isort --check-only (ensures imports are sorted)
- flake8 (checks for style violations)

### `type-check.sh`
Runs static type checking with mypy.

```bash
./scripts/type-check.sh
```

### `quality-check.sh`
Runs all quality checks including linting, type checking, and tests.

```bash
./scripts/quality-check.sh
```

This is useful before committing code or creating a pull request.

## Configuration

All tools are configured in:
- `pyproject.toml`: black, isort, and mypy settings
- `.flake8`: flake8-specific configuration

## Pre-commit Usage

Consider running `./scripts/format.sh` before committing to ensure code is properly formatted.
