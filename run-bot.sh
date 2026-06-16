#!/bin/bash

echo "Running database migrations..."
alembic upgrade head

echo "Starting bot..."
python app/bot_runner.py
