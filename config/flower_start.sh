#!/bin/bash
# Flower startup script
# Starts Flower with optional basic authentication.
# Reads DJANGO_FLOWER_* env vars from /home/ubuntu/app/.env (loaded by systemd).

set -e

cd /home/ubuntu/app || exit 1

DJANGO_SETTINGS_MODULE=${DJANGO_SETTINGS_MODULE:-core.settings}
FLOWER_PORT=${DJANGO_FLOWER_PORT:-5555}
FLOWER_ADDRESS=${DJANGO_FLOWER_ADDRESS:-127.0.0.1}

VENV_BIN="/home/ubuntu/app/env/bin/celery"
if [ ! -f "$VENV_BIN" ]; then
    echo "Error: Could not find celery binary at $VENV_BIN" >&2
    exit 1
fi

CMD="${VENV_BIN} -A core.celery.celery flower --port=${FLOWER_PORT} --address=${FLOWER_ADDRESS}"

if [ -n "$DJANGO_FLOWER_BASIC_AUTH" ]; then
    CMD="${CMD} --basic_auth=${DJANGO_FLOWER_BASIC_AUTH}"
fi

exec $CMD
