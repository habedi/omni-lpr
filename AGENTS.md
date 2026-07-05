# AGENTS.md

This file provides guidance to coding agents collaborating on this repository.

## Mission

Omni-LPR is a self-hostable server that provides automatic license plate recognition (ALPR) capabilities.
It exposes processing endpoints through a REST API and the Model Context Protocol (MCP), enabling integration with general software applications and AI agents.

Priorities, in order:

1. Correctness of license plate detection, text recognition, and model configurations.
2. Standard-compliant implementations of the REST API and the MCP interface.
3. Test suite coverage, including unit, integration, and E2E cases.
4. Structured logging, detailed error handling, and schema validation.

## Core Rules

- Use English for code, comments, docs, and tests.
- Prefer small, focused changes over broad refactoring.
- Add comments only when they clarify non-obvious behavior.
- Do not add features, error handling, or abstractions beyond what is needed for the current task.
- Keep dependencies small. Do not add heavy ML libraries, external packages, or extra services without prior discussion.

## Writing Style

- Use Oxford commas in inline lists: "a, b, and c" not "a, b, c".
- Do not use em dashes. Restructure the sentence, or use a colon or semicolon instead.
- Avoid colorful adjectives and adverbs. Write "graph generator" not "powerful graph generator".
- Prefer using noun phrases for checklist items, not imperative verbs. Write "negative weight detection" not "detect negative weights".
- Headings in Markdown files must be in title case: "Build from Source" not "Build from source". Minor words
  (a, an, the, and, but, or, for, in, on, at, to, by, of, from, and with) stay lowercase unless they are the first word.
- Write correct and complete sentences.
- Avoid made-up words, abbreviations, and colons in the middle of sentences.
- Don't use pretentious language and made-up words.

## Repository Layout

- `src/omni_lpr/__init__.py`: Package initialization and metadata.
- `src/omni_lpr/__main__.py`: CLI entry point and server startup logic.
- `src/omni_lpr/api_models.py`: Pydantic data schemas for API requests and responses.
- `src/omni_lpr/errors.py`: Exception definitions and API error handlers.
- `src/omni_lpr/event_store.py`: Client event log store.
- `src/omni_lpr/mcp.py`: MCP server implementation.
- `src/omni_lpr/rest.py`: Starlette REST API endpoints and Swagger documentation configuration.
- `src/omni_lpr/settings.py`: Application configuration settings parsing environment variables.
- `src/omni_lpr/tools.py`: Core ALPR operations, model management, and backend interfaces.
- `tests/`: Test suite containing unit, integration, and end-to-end test cases.
- `examples/`: Client integration examples for the REST and MCP endpoints.
- `docs/`: Repository documentation.
- `Dockerfile`: Deployment container definitions.
- `Makefile`: Script runner definitions for development tasks.

## Architecture

### REST and MCP Interfaces

The server exposes both a REST API and an MCP stream.
Both interfaces utilize the shared registry of tools defined in the package.
This unified design ensures consistent behavior across both standard REST calls and agentic MCP environments.

### Tool Engine

The core logic interfaces with `fast-alpr` and `fast-plate-ocr`.
Models execute using CPU, CUDA, or OpenVINO based on the current settings.
Operations support multiple formats: files, remote URLs, and Base64-encoded strings.

### Request Lifecycle

Incoming requests are parsed and validated by Pydantic models.
Starlette handles request routing and non-blocking asynchronous execution.
Correctness and speed of detection are prioritized during OCR processing.

## Python Conventions

- Python version: `>=3.10,<4.0` as declared in `pyproject.toml`.
- Dependency management uses Poetry.
- Formatting, linting, and import sorting use Ruff.
- Typechecking uses MyPy.
- Tests use PyTest.
- Prefer `pathlib.Path`, typed function signatures where practical, and deterministic ordering in generated outputs.

## Required Validation

Run the relevant targets for any change:

| Target            | Command            | What It Runs                                                     |
|-------------------|--------------------|------------------------------------------------------------------|
| Lint check        | `make lint`        | Ruff checks and automatic style corrections.                     |
| Formatting        | `make format`      | Ruff code formatting alignment.                                  |
| Type checks       | `make typecheck`   | MyPy static analysis.                                            |
| Unit tests        | `make test`        | PyTest validation of tools, server, and MCP endpoints.           |
| REST API examples | `make example-rest`| Verification of REST endpoints using example scripts.            |
| MCP API examples  | `make example-mcp` | Verification of MCP endpoints using example scripts.             |

## First Contribution Flow

1. Review of relevant modules under `src/omni_lpr/`.
2. Minimal code changes required for the feature or fix.
3. Added or updated tests targeting the modified components.
4. Syntax, formatting, and type checks passing status.
5. Local test suite validation via `make test`.

## Testing Expectations

- Tool updates validation using test data images under `tests/testdata/`.
- API model schema validation tests.
- Protocol compatibility validation against client script behaviors in `examples/`.
- Coverage level maintenance for new endpoints and schemas.

## Change Design Checklist

Before coding:

1. Identification of affected layers, including CLI, REST API, MCP server, tools, or validation schemas.
2. Input constraints and validation rules.
3. Hardware acceleration requirements and concurrency implications.
4. Backward compatibility check.

Before submitting:

1. Success status for linter and formatter checks.
2. Strict type compliance validation with `mypy`.
3. Test suite coverage verification.
4. Functional validation using REST and MCP examples.

## Commit and PR Hygiene

- Commits scoped to one logical change.
- PR descriptions including:
    1. Behavioral change summary.
    2. Verification of added or updated tests.
    3. Execution logs for local runs and tests.
