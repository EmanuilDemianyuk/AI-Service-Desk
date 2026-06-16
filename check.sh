#!/bin/bash

# Run tests
echo "Running tests..."
pytest

# Run type checking
echo "Running type checking..."
mypy app/

# Run linting
echo "Running linting..."
flake8 app/

# Run formatting check
echo "Checking code formatting..."
black --check app/

# Run import sorting check
echo "Checking import sorting..."
isort --check-only app/

echo "All checks passed!"
