<div align="center">
  <picture>
    <img alt="Omni-LPR Logo" src="logo.svg" width="300">
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
and the Model Context Protocol (MCP). It can be used both as a standalone ALPR microservice and as an ALPR toolbox for
AI agents and large language models (LLMs).

## Why Omni-LPR?

- **Decoupling:** Your main application can be in any programming language. It doesn't need to be tangled up with Python
  or specific ML dependencies because the server handles all of that.
- **Multiple Interfaces:** Communicate via a standard REST API or using the Model Context Protocol (MCP), which is
  designed for AI agent integration.
- **Ready-to-Deploy:** Pre-built Docker images are available for easy deployment.
- **Hardware Acceleration:** Optimized for different hardware backends, supporting generic CPUs (ONNX), Intel CPUs (
  OpenVINO), and NVIDIA GPUs (CUDA).
- **Asynchronous I/O:** Built on Starlette for high-performance, non-blocking I/O that can handle many concurrent
  requests.
- **Scalability:** As a separate microservice, it can be scaled independently of your main application.

> [!IMPORTANT]
> Omni-LPR is in early development, so bugs and breaking API changes are expected.
> Please use the [issues page](https://github.com/habedi/omni-lpr/issues) to report bugs or request features.

## Quickstart

You can get started with Omni-LPR in a few minutes by following the steps described below.

### 1. Install the Server

You can install Omni-LPR using `pip`:

```sh
pip install omni-lpr
```

### 2. Start the Server

When installed, start the server with a single command:

```sh
omni-lpr
```

By default, the server will be listening on `http://127.0.0.1:8000`.
You can confirm it's running by accessing the health check endpoint:

```sh
curl http://127.0.0.1:8000/api/health
# Expected output: {"status": "ok", "version": "0.2.0"}
```

### 3. Recognize a License Plate

Now you can make a request to recognize a license plate from an image.
The example below uses a publicly available image URL.

```sh
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"path": "https://www.olavsplates.com/foto_n/n_cx11111.jpg"}' \
  http://127.0.0.1:8000/api/v1/tools/detect_and_recognize_plate_from_path/invoke
```

You should receive a JSON response with the detected license plate information.

## Usage

Omni-LPR exposes its capabilities as "tools" that can be called via a REST API or over the MCP.

### Core Tools

- **`list_models`**: Lists the available license plate detector and OCR models.
- **`recognize_plate`**: Recognizes text from a pre-cropped image of a license plate.
- **`detect_and_recognize_plate`**: Detects and recognizes all license plates in a full image.

The server can accept an image in three ways: a Base64-encoded string, a local file path or a URL, or as a direct file
upload. For more details on how to use the different tool variations, please see
the [API Documentation](docs/README.md).

### REST API

The REST API provides a standard way to interact with the server. All tool endpoints are available under the `/api/v1`
prefix. Once the server is running, you can access interactive API documentation in the Swagger UI
at [http://127.0.0.1:8000/apidoc/swagger](http://127.0.0.1:8000/apidoc/swagger).

### MCP Interface

The server also exposes its tools over the Model Context Protocol (MCP) for integration with AI agents and LLMs. The MCP
endpoint is available at `http://127.0.0.1:8000/mcp/sse`.

You can use a tool like [MCP Inspector](https://github.com/modelcontextprotocol/inspector) to explore the available MCP
tools.

<div align="center">
  <picture>
    <img src="docs/assets/screenshots/mcp-inspector-2.png" alt="MCP Inspector Screenshot" width="auto">
  </picture>
</div>

The following examples show how to use the server with [LMStudio](https://lmstudio.ai/).

<div align="center">
  <picture>
    <img src="docs/assets/screenshots/lmstudio-list-models-1.png" alt="LMStudio Screenshot 1" width="auto">
  </picture>
</div>

<div align="center">
  <picture>
    <img src="docs/assets/screenshots/lmstudio-detect-plates-1.png" alt="LMStudio Screenshot 2" width="auto">
  </picture>
</div>

## Documentation

For detailed information on installation, configuration, and advanced usage, please see the [documentation in the
`docs` directory](docs/README.md). For usage examples, check out the [`examples`](examples) directory.

## Contributing

Contributions are always welcome!
Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details on how to get started.

## License

Omni-LPR is licensed under the MIT License (see [LICENSE](LICENSE)).

## Acknowledgements

- This project uses the awesome [fast-plate-ocr](https://github.com/ankandrew/fast-plate-ocr)
  and [fast-alpr](https://github.com/ankandrew/fast-alpr) Python libraries.
- The project logo is from [SVG Repo](https://www.svgrepo.com/svg/237124/license-plate-number).
