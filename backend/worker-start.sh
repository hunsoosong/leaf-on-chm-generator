#!/bin/bash

set -o errexit
set -o nounset

celery -A app.celery.tasks worker -l info -c 4
