#!/usr/bin/env bash
set -e

# Upgrade pip
python3 -m ensurepip --upgrade || true
pip install --upgrade pip

# Install dependencies
pip install --no-cache-dir -r requirements.txt

# Run bot
exec python3 waffle_bot_live.py

