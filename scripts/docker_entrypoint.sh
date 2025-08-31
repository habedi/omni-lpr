#!/usr/bin/env bash
set -euo pipefail

echo "Container entrypoint executing..."
echo "Starting the Omni-LPR server with Gunicorn..."

# Defaults (can be overridden at runtime with -e)
: "${GUNICORN_WORKERS:=4}"
: "${HOST:=0.0.0.0}"
: "${PORT:=8000}"
: "${GUNICORN_EXTRA_ARGS:=}"

VENV_BIN="/home/appuser/app/.venv/bin"
GUNICORN_BIN="${VENV_BIN}/gunicorn"

# Make sure Python can import the package in `src/`
export PYTHONPATH="/home/appuser/app/src:${PYTHONPATH:-}"

if [ ! -x "${GUNICORN_BIN}" ]; then
  echo "Error: gunicorn not found at ${GUNICORN_BIN}"
  echo "Contents of ${VENV_BIN}:"
  ls -la "${VENV_BIN}" || true
  exit 1
fi

export PATH="${VENV_BIN}:$PATH"

BIND="${HOST}:${PORT}"

# Word-split GUNICORN_EXTRA_ARGS and store them in an array.
read -ra GUNICORN_EXTRA_ARGS_ARRAY <<< "${GUNICORN_EXTRA_ARGS:-}"
echo "Running: ${GUNICORN_BIN} -w ${GUNICORN_WORKERS} -k uvicorn.workers.UvicornWorker --bind ${BIND} ${GUNICORN_EXTRA_ARGS} omni_lpr:starlette_app"

# Exec so Gunicorn is PID 1
exec "${GUNICORN_BIN}" \
    -w "${GUNICORN_WORKERS}" \
    -k uvicorn.workers.UvicornWorker \
    --bind "${BIND}" \
    --access-logfile "-" \
    --access-logformat '{"time": "%(t)s", "remote_addr": "%(h)s", "request": "%(r)s", "status": %(s)s, "bytes": %(b)s, "referer": "%(f)s", "user_agent": "%(a)s"}' \
    "${GUNICORN_EXTRA_ARGS_ARRAY[@]}" \
    omni_lpr:starlette_app
