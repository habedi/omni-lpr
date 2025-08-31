<div align="center">
  <picture>
    <img alt="Omni-LPR Logo" src="logo.svg" height="30%" width="30%">
  </picture>
<br>

<h2>Omni-LPR</h2>

[![Tests](https://img.shields.io/github/actions/workflow/status/habedi/omni-lpr/tests.yml?label=tests&style=flat&labelColor=333333&logo=github&logoColor=white)](https://github.com/habedi/omni-lpr/actions/workflows/tests.yml)
[![Code Coverage](https://img.shields.io/codecov/c/github/habedi/omni-lpr?style=flat&label=coverage&labelColor=333333&logo=codecov&logoColor=white)](https://codecov.io/gh/habedi/omni-lpr)
[![Code Quality](https://img.shields.io/codefactor/grade/github/habedi/omni-lpr?style=flat&label=code%20quality&labelColor=333333&logo=codefactor&logoColor=white)](https://www.codefactor.io/repository/github/habedi/omni-lpr)
[![Python Version](https://img.shields.io/badge/python-%3E=3.10-3776ab?style=flat&labelColor=333333&logo=python&logoColor=white)](https://github.com/habedi/omni-lpr)
[![PyPI](https://img.shields.io/pypi/v/omni-lpr?style=flat&labelColor=333333&logo=pypi&logoColor=white)](https://pypi.org/project/omni-lpr/)
[![Examples](https://img.shields.io/github/v/tag/habedi/omni-lpr?label=examples&color=green&style=flat&labelColor=282c34&logo=python&logoColor=white)](https://github.com/habedi/omni-lpr/tree/main/examples)
[![License](https://img.shields.io/badge/license-MIT-00acc1?style=flat&labelColor=333333&logo=open-source-initiative&logoColor=white)](https://github.com/habedi/omni-lpr/blob/main/LICENSE)
<br>
[![Docker Image (CPU)](https://img.shields.io/github/v/release/habedi/omni-lpr?label=image%20(cpu)&logo=docker&logoColor=white&style=flat&color=007ec6)](https://github.com/habedi/omni-lpr/pkgs/container/omni-lpr-cpu)
[![Docker Image (OpenVINO)](https://img.shields.io/github/v/release/habedi/omni-lpr?label=image%20(openvino)&logo=docker&logoColor=white&style=flat&color=007ec6)](https://github.com/habedi/omni-lpr/pkgs/container/omni-lpr-openvino)
[![Docker Image (CUDA)](https://img.shields.io/github/v/release/habedi/omni-lpr?label=image%20(cuda)&logo=docker&logoColor=white&style=flat&color=007ec6)](https://github.com/habedi/omni-lpr/pkgs/container/omni-lpr-cuda)

A multi-interface (REST and MCP) server for automatic license plate recognition

</div>

---

Omni-LPR is a self-hostable server that provides automatic license plate recognition (ALPR) capabilities via a REST API
and over the Model Context Protocol (MCP).
It can be used both as a standalone ALPR microservice and as an ALPR toolbox for AI agents and LLMs.

### Why Omni-LPR?

Using Omni-LPR can have the following benefits:

- **Decoupling.** Your main application can be in any programming language. It doesn't need to be tangled up with
  Python or specific ML dependencies because the server handles all of that.

- **Multiple Interfaces.** You aren't locked into one way of communicating. You can use a standard REST API from any
  app, or you can use MCP, which is designed for AI agent integration.

- **Ready-to-Deploy.** You don't have to build it from scratch. There are pre-built Docker images that are easy to
  deploy and start using immediately.

- **Hardware Acceleration.** The server is optimized for the hardware you have. It supports generic CPUs (ONNX), Intel
  CPUs (OpenVINO), and NVIDIA GPUs (CUDA).

- **Asynchronous I/O.** It's built on Starlette, which means it has high-performance, non-blocking I/O. It can handle
  many concurrent requests without getting bogged down.

- **Scalability.** Because it's a separate service, it can be scaled independently of your main application. If you
  suddenly need more ALPR power, you can scale Omni-LPR up without touching anything else.

> [!IMPORTANT]
> Omni-LPR is in early development, so bugs and breaking API changes are expected.
> Please use the [issues page](https://github.com/habedi/omni-lpr/issues) to report bugs or request features.

---

### Quickstart

You can install and run Omni-LPR server locally using the commands shown below.

```sh
# Install the server
pip install omni-lpr

# Start the server
omni-lpr
```

By default, the server will be listening to requests on port `8000` of `localhost`.
You can check out the tools that the server provides over MCP using a tool like
[MCP Inspector](https://github.com/modelcontextprotocol/inspector)
(at [http://localhost:8000/mcp/sse](http://localhost:8000/mcp/sse)).
You can also see the REST API definition in the Swagger UI
at [http://127.0.0.1:8000/apidoc/swagger](http://127.0.0.1:8000/apidoc/swagger).

The figure below shows a screenshot of the MCP Inspector tool connected to the Omni-LPR server and showing the
available tools.

<div align="center">
  <picture>
<img src="docs/assets/screenshots/mcp-inspector-2.png" alt="MCP Inspector Screenshot" width="auto" height="auto">
</picture>
</div>

### Integration

You can connect any client that supports the MCP protocol to the server.
The following examples show how to use the server with [LMStudio](https://lmstudio.ai/).

#### LMStudio Configuration

```json
{
    "mcpServers": {
        "omni-lpr-local": {
            "url": "http://localhost:8000/mcp/sse"
        }
    }
}
```

#### LMStudio Example Usages

Below is an example of listing the available models in the server.

<div align="center">
  <picture>
<img src="docs/assets/screenshots/lmstudio-list-models-1.png" alt="LMStudio Screenshot 1" width="auto" height="auto">
</picture>
</div>

Below is an example of detecting the license plates in
an [image available on the web](https://www.olavsplates.com/foto_n/n_cx11111.jpg).

<div align="center">
  <picture>
<img src="docs/assets/screenshots/lmstudio-detect-plates-1.png" alt="LMStudio Screenshot 2" width="auto" height="auto">
  </picture>
</div>

---

### Documentation

Omni-LPR's documentation is available [here](docs).

### Examples

Check out the [examples](examples) directory for usage examples.

---

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

- **Performance**

    - [x] Asynchronous I/O for concurrent requests.
    - [x] Prometheus metrics endpoint (`/api/metrics`).
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

---

### Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for details on how to make a contribution.

### License

Omni-LPR is licensed under the MIT License (see [LICENSE](LICENSE)).

### Acknowledgements

- This project uses the awesome [fast-plate-ocr](https://github.com/ankandrew/fast-plate-ocr)
  and [fast-alpr](https://github.com/ankandrew/fast-alpr) Python libraries.
- The project logo is from [SVG Repo](https://www.svgrepo.com/svg/237124/license-plate-number).
