#!/bin/bash

echo "Running black..."
black app/

echo "Running isort..."
isort app/

echo "Code formatting complete!"
