#!/usr/bin/env bash
set -e

# re-install everything into the buildpack's virtualenv
pip install --no-cache-dir -r requirements.txt

# hand off to your bot
exec python woffle_bot_live.py
