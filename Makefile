# Load environment variables from .env file
ifneq (,$(wildcard ./.env))
    include .env
    export $(shell sed 's/=.*//' .env)
else
    $(warning .env file not found. Environment variables not loaded.)
endif

# ==============================================================================
# VARIABLES
# ==============================================================================
PYTHON      ?= python3
PIP         ?= pip3
DEP_MNGR    ?= poetry
DOCS_DIR    ?= docs

# Server configuration (can be overridden by environment variables)
TRANSPORT ?= sse
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
help: ## Show help messages for all available targets
	@grep -E '^[a-zA-Z_-]+:.*## .*$$' Makefile | \
	awk 'BEGIN {FS = ":.*## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'


# ==============================================================================
# SETUP & INSTALLATION
# ==============================================================================
.PHONY: setup
setup: ## Install system dependencies and dependency manager (e.g., Poetry)
	sudo apt-get update
	sudo apt-get install -y python3-pip docker.io docker-compose
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
run: ## Run the MCP server application
	@echo "Starting MCP server..."
	$(DEP_MNGR) run mcp-server


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
# DOCKER
# ==============================================================================
.PHONY: docker-build
docker-build: ## Build the Docker image for the server
	docker build -t template-mcp-server .

.PHONY: docker-run
docker-run: ## Run the server inside a Docker container
	docker run --rm -it -p $(PORT):$(PORT) template-mcp-server


# ==============================================================================
# MAINTENANCE
# ==============================================================================
.PHONY: clean
clean: ## Remove caches and build artifacts
	find . -type f -name '*.pyc' -delete
	find . -type d -name '__pycache__' -exec rm -rf {} +
	rm -rf $(CACHE_DIRS) $(COVERAGE) $(DIST_DIRS) $(TMP_DIRS)
