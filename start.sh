#!/usr/bin/env sh
# Start Phone Clicker on macOS or Linux.
set -e
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  echo "Setting up for the first time..."
  python3 -m venv .venv
fi
# Quick when everything is already installed; picks up new dependencies after an update.
.venv/bin/python -m pip install -q --disable-pip-version-check -r requirements.txt
exec .venv/bin/python server.py "$@"
