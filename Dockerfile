# File: Dockerfile
ARG BACKEND=cpu

FROM python:3.12-slim-trixie as builder
ARG BACKEND
COPY --from=ghcr.io/astral-sh/uv:0.12.1 /uv /usr/local/bin/uv
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DEBIAN_FRONTEND=noninteractive

WORKDIR /app

COPY pyproject.toml uv.lock README.md LICENSE ./
COPY ./src ./src
COPY ./scripts ./scripts
COPY Makefile ./

RUN case ${BACKEND} in \
        cuda) uv export --locked --no-dev --no-emit-project --extra cuda -o requirements.txt ;; \
        openvino) uv export --locked --no-dev --no-emit-project --extra openvino -o requirements.txt ;; \
        *) uv export --locked --no-dev --no-emit-project -o requirements.txt ;; \
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
COPY --from=builder /usr/local/bin/uv /usr/local/bin/uv

RUN apt-get update && apt-get install -y --no-install-recommends \
        libglib2.0-0 libgl1 libsm6 libxext6 libxrender1 && \
    rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --shell /bin/bash appuser && mkdir -p /home/appuser/app

WORKDIR /home/appuser/app

COPY --from=common /home/appuser/app /home/appuser/app

RUN uv venv --python python /home/appuser/app/.venv && \
    uv pip install --python .venv/bin/python --no-deps --no-cache -r requirements.txt && \
    uv pip install --python .venv/bin/python --no-deps --no-cache . && \
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
COPY --from=builder /usr/local/bin/uv /usr/local/bin/uv

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3.11 python3.11-venv python3-pip \
        libglib2.0-0 libgl1 libsm6 libxext6 libxrender1 && \
    rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --shell /bin/bash appuser && mkdir -p /home/appuser/app

WORKDIR /home/appuser/app

COPY --from=common /home/appuser/app /home/appuser/app

RUN uv venv --python python3.11 /home/appuser/app/.venv && \
    uv pip install --python .venv/bin/python --no-deps --no-cache -r requirements.txt && \
    uv pip install --python .venv/bin/python --no-deps --no-cache . && \
    chown -R appuser:appuser /home/appuser/app

USER appuser

ENV PATH="/home/appuser/app/.venv/bin:$PATH"

EXPOSE 8000

ENTRYPOINT ["/bin/bash", "/home/appuser/app/scripts/docker_entrypoint.sh"]
