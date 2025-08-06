#!/usr/bin/env bash
set -e

# bootstrap pip inside the buildpack venv
python -m ensurepip --upgrade

# reinstall your dependencies
python -m pip install --no-cache-dir -r requirements.txt

# hand off to your bot
exec python woffle_bot_live.py
