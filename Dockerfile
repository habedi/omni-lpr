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
    apt-get install -qy --no-install-recommends python3-pip make && \
    pip install --no-cache-dir poetry && \
    poetry self add poetry-plugin-export && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md LICENSE ./
COPY ./src ./src
COPY ./scripts ./scripts
COPY Makefile ./

RUN case ${BACKEND} in \
        cuda) poetry export -f requirements.txt --without-hashes --extras cuda -o requirements.txt ;; \
        openvino) poetry export -f requirements.txt --without-hashes --extras openvino -o requirements.txt ;; \
        *) poetry export -f requirements.txt --without-hashes -o requirements.txt ;; \
    esac

FROM builder as common
WORKDIR /home/appuser/app
COPY --from=builder /app/requirements.txt ./requirements.txt
COPY --from=builder /app/pyproject.toml ./pyproject.toml
COPY --from=builder /app/README.md ./README.md
COPY --from=builder /app/LICENSE ./LICENSE
COPY --from=builder /app/src ./src
COPY --from=builder /app/scripts ./scripts
COPY --from=builder /app/Makefile ./Makefile

# --- Common final image base for CPU/OpenVINO ---
FROM python:3.12-slim-trixie as common-final

RUN apt-get update && apt-get install -y --no-install-recommends \
        libglib2.0-0 libgl1 libsm6 libxext6 libxrender1 && \
    rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --shell /bin/bash appuser && mkdir -p /home/appuser/app

WORKDIR /home/appuser/app

COPY --from=common /home/appuser/app /home/appuser/app

RUN python -m venv /home/appuser/app/.venv && \
    /home/appuser/app/.venv/bin/pip install --upgrade pip && \
    /home/appuser/app/.venv/bin/pip install --no-deps --no-cache-dir -r requirements.txt && \
    /home/appuser/app/.venv/bin/pip install --no-deps --no-cache-dir . && \
    chown -R appuser:appuser /home/appuser/app

USER appuser

ENV PATH="/home/appuser/app/.venv/bin:$PATH"

EXPOSE 8000

ENTRYPOINT ["/bin/bash", "/home/appuser/app/scripts/docker_entrypoint.sh"]

# --- CPU final image ---
FROM common-final as cpu

# --- OpenVINO final image ---
FROM common-final as openvino

# --- CUDA final image ---

FROM nvidia/cuda:12.2.0-runtime-ubuntu22.04 as cuda

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3.12 python3.12-venv python3-pip \
        libglib2.0-0 libgl1 libsm6 libxext6 libxrender1 && \
    rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --shell /bin/bash appuser && mkdir -p /home/appuser/app

WORKDIR /home/appuser/app

COPY --from=common /home/appuser/app /home/appuser/app

RUN python3.12 -m venv /home/appuser/app/.venv && \
    /home/appuser/app/.venv/bin/pip install --upgrade pip && \
    /home/appuser/app/.venv/bin/pip install --no-deps --no-cache-dir -r requirements.txt && \
    /home/appuser/app/.venv/bin/pip install --no-deps --no-cache-dir . && \
    chown -R appuser:appuser /home/appuser/app

USER appuser

ENV PATH="/home/appuser/app/.venv/bin:$PATH"

EXPOSE 8000

ENTRYPOINT ["/bin/bash", "/home/appuser/app/scripts/docker_entrypoint.sh"]
