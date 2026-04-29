# base image
FROM python:3.11-slim AS python-base

# build args
ARG INSTALL_DEV=false
ARG NUM_OF_WORKERS=1

# do not buffer log messages and do not write byte code .pyc
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    PYTHONUNBUFFERED=1

# set dev mode
ENV DEV_MODE=$INSTALL_DEV

# set path to conda environment
ENV CONDA_ENV_PATH=/opt/conda/envs/app

# set number of workers for uvicorn process
ENV UVICORN_WORKERS=$NUM_OF_WORKERS

# image for building python environment
FROM condaforge/miniforge3:latest AS conda-env-base

# do not write byte code .pyc
ENV PYTHONDONTWRITEBYTECODE=1

# env for conda environment file
ENV CONDA_ENV_DEPS=environment.yml

WORKDIR /opt

COPY $CONDA_ENV_DEPS ./

# allow installing dev dependencies to run tests
ARG INSTALL_DEV=false
RUN conda env create -f $CONDA_ENV_DEPS \
    && conda clean -afy \
    && find /opt/conda/ -follow -type f -name '*.pyc' -delete

# final stage
FROM python-base

WORKDIR /app/

# create app user
RUN useradd app

# copy over virtual environment
COPY --from=conda-env-base --chown=app:app $CONDA_ENV_PATH $CONDA_ENV_PATH

# update path to include venv bin
ENV PATH="$CONDA_ENV_PATH/bin:$PATH"

# add application environment variables
ENV DB_FILE="/var/lib/app/tasks.db"
ENV CELERY_BROKER_URL=redis://redis:6379/0
ENV CELERY_RESULT_BACKEND=redis://redis:6379/0

# copy over application code
COPY --chown=app:app . /app

# create directory for logs, temp files, and user uploads, and update permissions
RUN mkdir -p /var/lib/app \
    && mkdir -p /var/tmp/app \
    && mkdir /static \
    && chown -R app:app /var/lib/app \
    && chown -R app:app /var/tmp/app \
    && chown -R app:app /static

# change to non-root user
USER app

CMD /bin/bash /app/backend-start.sh
