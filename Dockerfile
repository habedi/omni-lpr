# File: Dockerfile
ARG BACKEND=cpu

FROM python:3.12-slim-trixie as builder
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_IN_PROJECT=true \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app
RUN apt-get update -q && \
    apt-get install -qy python3-pip make && \
    pip install --no-cache-dir poetry && \
    poetry self add poetry-plugin-export && \
    rm -rf /var/lib/apt/lists/*

# Copy project metadata and sources required to export runtime deps
COPY pyproject.toml README.md LICENSE ./
COPY ./src ./src
COPY ./scripts ./scripts
COPY Makefile ./

# Export requirements for the chosen backend so final stages can install with final-Python
RUN case ${BACKEND} in \
        cuda) \
            poetry export -f requirements.txt --without-hashes --extras cuda -o requirements.txt; \
            ;; \
        openvino) \
            poetry export -f requirements.txt --without-hashes --extras openvino -o requirements.txt; \
            ;; \
        *) \
            poetry export -f requirements.txt --without-hashes -o requirements.txt; \
            ;; \
    esac

FROM builder as common
WORKDIR /home/appuser/app

# Copy only exported requirements and app sources (do NOT copy builder .venv)
COPY --from=builder /app/requirements.txt ./requirements.txt
COPY --from=builder /app/src ./src
COPY --from=builder /app/scripts ./scripts
COPY --from=builder /app/Makefile ./Makefile

# --- CPU final image ---
FROM python:3.12-slim-trixie as cpu
RUN useradd --create-home --shell /bin/bash appuser && \
    mkdir -p /home/appuser/app
WORKDIR /home/appuser/app

COPY --from=common /home/appuser/app /home/appuser/app

# Create a fresh venv using this image's Python and install runtime deps only
RUN python -m venv /home/appuser/app/.venv && \
    /home/appuser/app/.venv/bin/pip install --upgrade pip && \
    /home/appuser/app/.venv/bin/pip install --no-deps --no-cache-dir -r /home/appuser/app/requirements.txt && \
    chown -R appuser:appuser /home/appuser/app

USER appuser
ENV PATH="/home/appuser/app/.venv/bin:$PATH"
EXPOSE 8000
ENTRYPOINT ["/bin/bash", "/home/appuser/app/scripts/docker_entrypoint.sh"]

# --- OpenVINO final image ---
FROM python:3.12-slim-trixie as openvino
RUN useradd --create-home --shell /bin/bash appuser && \
    mkdir -p /home/appuser/app
WORKDIR /home/appuser/app

COPY --from=common /home/appuser/app /home/appuser/app

RUN python -m venv /home/appuser/app/.venv && \
    /home/appuser/app/.venv/bin/pip install --upgrade pip && \
    /home/appuser/app/.venv/bin/pip install --no-deps --no-cache-dir -r /home/appuser/app/requirements.txt && \
    chown -R appuser:appuser /home/appuser/app

USER appuser
ENV PATH="/home/appuser/app/.venv/bin:$PATH"
EXPOSE 8000
ENTRYPOINT ["/bin/bash", "/home/appuser/app/scripts/docker_entrypoint.sh"]

# --- CUDA final image ---
FROM nvidia/cuda:13.0.0-runtime-ubuntu24.04 as cuda
RUN apt-get update && \
    apt-get install -y python3.12 python3.12-venv python3-pip && \
    rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --shell /bin/bash appuser && \
    mkdir -p /home/appuser/app
WORKDIR /home/appuser/app

COPY --from=common /home/appuser/app /home/appuser/app

# Create venv using installed python3.12 and install runtime deps
RUN python3.12 -m venv /home/appuser/app/.venv && \
    /home/appuser/app/.venv/bin/pip install --upgrade pip && \
    /home/appuser/app/.venv/bin/pip install --no-deps --no-cache-dir -r /home/appuser/app/requirements.txt && \
    chown -R appuser:appuser /home/appuser/app

USER appuser
ENV PATH="/home/appuser/app/.venv/bin:$PATH"
EXPOSE 8000
ENTRYPOINT ["/bin/bash", "/home/appuser/app/scripts/docker_entrypoint.sh"]
