#!/bin/bash

set -o errexit
set -o nounset

python /app/app/db/init_db.py

# start uvicorn server
if [[ "$DEV_MODE" = true ]]; then
    uvicorn app.main:app --host 0.0.0.0 --port 5000  --reload
else
    uvicorn app.main:app --proxy-headers --workers ${UVICORN_WORKERS} --host 0.0.0.0 --port 5000
fi