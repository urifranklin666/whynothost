#!/usr/bin/env bash
# WhyNotHost — one-command dev server
# Starts the FastAPI backend on :8022 serving the built frontend at /ui/
set -e
cd "$(dirname "$0")/backend"
if [ ! -d .venv ]; then
  python3 -m venv .venv
  .venv/bin/pip install -q -r requirements.txt
fi
if [ ! -f ../frontend/dist/ui/index.html ]; then
  echo "Frontend not built. Run: (cd ../frontend && npm install && npm run build)"
fi
exec .venv/bin/uvicorn app.main:app --port 8022 --host 0.0.0.0