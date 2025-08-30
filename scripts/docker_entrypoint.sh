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
echo "Running: ${GUNICORN_BIN} -w ${GUNICORN_WORKERS} -k uvicorn.workers.UvicornWorker omni_lpr:starlette_app --bind ${BIND} ${GUNICORN_EXTRA_ARGS}"

# Exec so Gunicorn is PID 1
exec "${GUNICORN_BIN}" -w "${GUNICORN_WORKERS}" -k uvicorn.workers.UvicornWorker omni_lpr:starlette_app --bind "${BIND}" "${GUNICORN_EXTRA_ARGS}"
