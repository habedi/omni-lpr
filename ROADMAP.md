## Feature Roadmap

This document includes the roadmap for the Omni-LPR project.
It outlines features to be implemented and their current status.

> [!IMPORTANT]
> This roadmap is a work in progress and is subject to change.

### Feature Roadmap

- **Core ALPR Capabilities**

    - [x] License plate detection.
    - [x] License plate recognition.
    - [x] Optimized models for CPU, OpenVINO, and CUDA backends.

- **Interfaces and Developer Experience**

    - [x] MCP interface for AI agent integration.
    - [x] REST API for all core functions/tools.
    - [x] Standardized JSON error responses.
    - [x] Interactive API documentation (Swagger UI and ReDoc).
    - [x] Support for direct image uploads (`multipart/form-data`).
    - [x] Switch from deprecated SSE to streamable HTTP for transport.

- **Performance**

    - [x] Asynchronous I/O for concurrent requests.
    - [x] Simple LRU cache for recently processed images.
    - [ ] Request batching for model inference.

- **Integrations**

    - [x] Standalone microservice architecture.
    - [x] MCP and REST API usage examples.
    - [ ] A Python client library to simplify interaction with the REST API.

- **Deployment**

    - [x] Pre-built Docker images for each hardware backend.
    - [x] Configuration via environment variables and CLI arguments.
    - [ ] A Helm chart for Kubernetes deployment.

- **Benchmarks**

    - [ ] Performance benchmarks for different hardware and request types.
