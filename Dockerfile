# Stage 1: Builder - Install dependencies and build artifacts
# Use an official Python slim image as a base
FROM python:3.11-slim as builder

# Set environment variables for a clean build
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV POETRY_NO_INTERACTION=1
ENV POETRY_VIRTUALENVS_IN_PROJECT=true
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Install 'make' and 'poetry', which are required for the build process
RUN apt-get update && apt-get install -y make && rm -rf /var/lib/apt/lists/*
RUN pip install poetry

# Copy project definition and Makefile to leverage Docker's layer caching
COPY poetry.lock pyproject.toml Makefile ./

# Use the Makefile to install dependencies. This keeps the build process
# consistent with the local development environment.
RUN make install


# Stage 2: Final Image - Create the lean runtime image
FROM python:3.11-slim as final

# Install 'make' which is required by the entrypoint script
RUN apt-get update && apt-get install -y make && rm -rf /var/lib/apt/lists/*

# Create a dedicated, non-root user for improved security
RUN useradd --create-home --shell /bin/bash appuser
USER appuser
WORKDIR /home/appuser/app

# Copy the virtual environment and Makefile from the builder stage
COPY --from=builder /app/.venv ./.venv
COPY --from=builder /app/Makefile ./

# Add the virtual environment's bin directory to the PATH
ENV PATH="/home/appuser/app/.venv/bin:$PATH"

# Copy the application source code and entrypoint script
# The destination 'server' matches the package structure in pyproject.toml
COPY ./src/server ./server
COPY ./scripts/docker_entrypoint.sh ./scripts/

# Make the entrypoint script executable
RUN chmod +x ./scripts/docker_entrypoint.sh

# Expose the default port for the SSE server
EXPOSE 8000

# Set the entrypoint to our script. This script will execute 'make run'.
ENTRYPOINT ["./scripts/docker_entrypoint.sh"]
