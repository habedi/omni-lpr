# ==============================================================================
# VARIABLES
# ==============================================================================
PYTHON      ?= python3
PIP         ?= pip3
DEP_MNGR    ?= poetry
DOCS_DIR    ?= docs
DOCKERFILE   ?= Dockerfile
GUNICORN_NUM_WORKERS ?= 4

# Server configuration (can be overridden by environment variables)
PORT      ?= 8000
HOST      ?= 0.0.0.0

# Directories and files to clean
CACHE_DIRS  = .mypy_cache .pytest_cache .ruff_cache
COVERAGE    = .coverage htmlcov coverage.xml
DIST_DIRS   = dist junit
TMP_DIRS    = site

.DEFAULT_GOAL := help

# ==============================================================================
# HELP
# ==============================================================================
.PHONY: help
help: ## Show the help messages for all targets
	@echo "Usage: make <target>"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*## .*$$' Makefile | \
	awk 'BEGIN {FS = ":.*## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

# ==============================================================================
# SETUP & INSTALLATION
# ==============================================================================
.PHONY: setup
setup: ## Install system dependencies and dependency manager (e.g., Poetry)
	sudo apt-get update
	sudo apt-get install -y python3-pip docker.io
	$(PIP) install --upgrade pip
	$(PIP) install $(DEP_MNGR)

.PHONY: install
install: ## Install Python dependencies
	$(DEP_MNGR) install --all-extras --no-interaction

# ==============================================================================
# QUALITY & TESTING
# ==============================================================================
.PHONY: test
test: ## Run tests
	$(DEP_MNGR) run pytest

.PHONY: lint
lint: ## Run linter checks
	$(DEP_MNGR) run ruff check --fix

.PHONY: format
format: ## Format code
	$(DEP_MNGR) run ruff format

.PHONY: typecheck
typecheck: ## Typecheck code
	$(DEP_MNGR) run mypy .

.PHONY: setup-hooks
setup-hooks: ## Install Git hooks (pre-commit and pre-push)
	$(DEP_MNGR) run pre-commit install --hook-type pre-commit
	$(DEP_MNGR) run pre-commit install --hook-type pre-push
	$(DEP_MNGR) run pre-commit install-hooks

.PHONY: test-hooks
test-hooks: ## Test Git hooks on all files
	$(DEP_MNGR) run pre-commit run --all-files

# ==============================================================================
# APPLICATION
# ==============================================================================
.PHONY: run
run: ## Start the server
	@echo "Starting the server..."
	$(DEP_MNGR) run omni-lpr --host $(HOST) --port $(PORT) --log-level DEBUG

.PHONY: run-gunicorn
run-gunicorn: ## Start the server with Gunicorn
	@echo "Starting the Omni-LPR server with Gunicorn..."
	$(DEP_MNGR) run gunicorn -w $(GUNICORN_NUM_WORKERS) -k uvicorn.workers.UvicornWorker omni_lpr:starlette_app

# ==============================================================================
# BUILD & PUBLISH
# ==============================================================================
.PHONY: build
build: ## Build distributions
	$(DEP_MNGR) build

.PHONY: publish
publish: ## Publish to PyPI (requires PYPI_TOKEN)
	$(DEP_MNGR) config pypi-token.pypi $(PYPI_TOKEN)
	$(DEP_MNGR) publish --build

# ==============================================================================
# EXAMPLES
# ==============================================================================
.PHONY: example-rest example-mcp

SERVER_PID := /tmp/omni-lpr-server.pid

# Define the lists of example files
REST_EXAMPLES := $(wildcard examples/rest_*_example.py)
MCP_EXAMPLES := $(wildcard examples/mcp_*_example.py)

define run_examples
	@echo "Starting server in background..."
	$(DEP_MNGR) run omni-lpr > /dev/null 2>&1 & echo $$! > $(SERVER_PID)
	@echo "Waiting for server to start..."
	@while ! nc -z localhost 8000; do sleep 1; done
	@echo "Server started. Running $(1) examples..."
	@for example in $(2); do \
		echo "\n--- Running $$example ---"; \
		$(DEP_MNGR) run python $$example; \
	done
	@echo "\nStopping server..."
	@kill `cat $(SERVER_PID)`
endef

example-rest: ## Run all REST API examples
	$(call run_examples,"REST",$(REST_EXAMPLES))

example-mcp: ## Run all MCP API examples
	$(call run_examples,"MCP",$(MCP_EXAMPLES))

# ==============================================================================
# DOCKER
# ==============================================================================
IMAGE_NAME ?= omni-lpr

.PHONY: docker-build-cpu
docker-build-cpu: ## Build the Docker image for CPU
	docker build -t $(IMAGE_NAME):cpu --build-arg BACKEND=cpu --target cpu -f Dockerfile .

.PHONY: docker-build-cuda
docker-build-cuda: ## Build the Docker image for CUDA
	docker build -t $(IMAGE_NAME):cuda --build-arg BACKEND=cuda --target cuda -f Dockerfile .

.PHONY: docker-build-openvino
docker-build-openvino: ## Build the Docker image for OpenVINO
	docker build -t $(IMAGE_NAME):openvino --build-arg BACKEND=openvino --target openvino -f Dockerfile .

.PHONY: docker-build
docker-build: docker-build-cpu ## Build the default Docker image (CPU)

.PHONY: docker-run-cpu
docker-run-cpu: ## Run the CPU Docker container
	docker run --rm -it -p $(PORT):$(PORT) $(IMAGE_NAME):cpu

.PHONY: docker-run-cuda
docker-run-cuda: ## Run the CUDA Docker container
	docker run --rm -it --gpus all -p $(PORT):$(PORT) $(IMAGE_NAME):cuda

.PHONY: docker-run-openvino
docker-run-openvino: ## Run the OpenVINO Docker container
	docker run --rm -it -p $(PORT):$(PORT) $(IMAGE_NAME):openvino

.PHONY: docker-run
docker-run: docker-run-cpu ## Run the default Docker container (CPU)

# ==============================================================================
# MAINTENANCE
# ==============================================================================
.PHONY: clean
clean: ## Remove caches and build artifacts
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -exec rm -rf {} +
	rm -rf $(CACHE_DIRS) $(COVERAGE) $(DIST_DIRS) $(TMP_DIRS)

## ==============================================================================
# DOCUMENTATION
# ==============================================================================

.PHONY: docs
docs: ## Generate the project documentation
	$(DEP_MNGR) run mkdocs build
