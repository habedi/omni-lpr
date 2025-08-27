<div align="center">
  <picture>
    <img alt="Omni-LPR Logo" src="logo.svg" height="25%" width="25%">
  </picture>
<br>

<h2>Omni-LPR</h2>

[![Tests](https://img.shields.io/github/actions/workflow/status/habedi/omni-lpr/tests.yml?label=tests&style=flat&labelColor=333333&logo=github&logoColor=white)](https://github.com/habedi/omni-lpr/actions/workflows/tests.yml)
[![Code Coverage](https://img.shields.io/codecov/c/github/habedi/omni-lpr?style=flat&label=coverage&labelColor=333333&logo=codecov&logoColor=white)](https://codecov.io/gh/habedi/omni-lpr)
[![Code Quality](https://img.shields.io/codefactor/grade/github/habedi/omni-lpr?style=flat&label=code%20quality&labelColor=333333&logo=codefactor&logoColor=white)](https://www.codefactor.io/repository/github/habedi/omni-lpr)
[![Python Version](https://img.shields.io/badge/python-%3E=3.10-3776ab?style=flat&labelColor=333333&logo=python&logoColor=white)](https://github.com/habedi/omni-lpr)
[![PyPI](https://img.shields.io/pypi/v/omni-lpr?style=flat&labelColor=333333&logo=pypi&logoColor=white)](https://pypi.org/project/omni-lpr/)
[![License](https://img.shields.io/badge/license-MIT-00acc1?style=flat&labelColor=333333&logo=open-source-initiative&logoColor=white)](https://github.com/habedi/omni-lpr/blob/main/LICENSE)

A multiprotocol (REST and MCP) server for automatic license plate recognition

</div>

---

Omni-LPR is a self-hostable server that provides automatic license plate recognition (APLR) capabilities over REST and
the Model Context Protocol (MCP) APIs.
It can be both seen as a standalone ALPR microservice or as an ALPR toolbox for AI agents.

### Why Omni-LPR?

Instead of integrating complex machine learning (ML) libraries directly into your application, Omni-LPR provides a
ready-to-deploy server that offers:

- **Decoupling:** Run your recognition model as a separate service. Your main application (in any language) doesn't need
  Python or ML dependencies.
- **Multiple Interfaces:** Consume the service via a standard REST API, or the MCP for AI agent
  integration.
- **Ready-to-Deploy:** Easy to deploy and start with Docker, Gunicorn, and multiple hardware backends support out of the
  box.
- **Scalability:** Scale your recognition service independently of your main application.

### Features

- **Multiple API Interfaces:** REST and MCP support.
- **High-Performance Recognition:** Fast and accurate license place recognition (detection and recognition) using
  state-of-the-art computer vision models.
- **Hardware Acceleration:** Support for CPU (ONNX), Intel CPU/VPU (OpenVINO), and NVIDIA GPU (CUDA).
- **Easy Deployment:** Installable as a Python library or runnable via pre-built Docker images in a container.
- **Asynchronous Core:** Built on Starlette for high-performance, non-blocking I/O.

---

### Getting Started

You can run Omni-LPR either by installing it as a Python library or by using a pre-built Docker image.

#### Method 1

You can install Omni-LPR via `pip` or any other Python package manager.

```sh
pip install omni-lpr
````

By default, the server will use the CPU-enabled ONNX models for both detection and OCR.
To use hardware-accelerated models, you need to install the extra dependencies:

- **OpenVINO (Intel CPUs):** `pip install omni-lpr[openvino]`
- **CUDA (NVIDIA GPUs):** `pip install omni-lpr[cuda]`

##### Starting the Server

To start the server with the REST and MCP APIs, set the `TRANSPORT` environment variable to `sse` and run the
`omni-lpr` command:

```sh
TRANSPORT=sse omni-lpr --host 0.0.0.0 --port 8000
```

#### Method 2

Pre-built Docker images are available from the GitHub Container Registry (`ghcr.io`).
You can build the images locally or pull them from the registry.

##### Building the Docker Images

You can build the Docker images for different backends using the provided `Makefile`:

- **CPU (default):** `make docker-build-cpu`
- **CUDA:** `make docker-build-cuda`
- **OpenVINO:** `make docker-build-openvino`

##### Running the Container

Once you have built or pulled the images, you can run them using the following commands:

- **CPU Image (ONNX):**
  ```sh
  make docker-run-cpu

  # or manually:
  docker run --rm -it -p 8000:8000 ghcr.io/habedi/omni-lpr:cpu
  ```

- **CPU Image (OpenVINO):**
  ```sh
  make docker-run-openvino
  # or manually:
  docker run --rm -it -p 8000:8000 ghcr.io/habedi/omni-lpr:openvino
  ```

- **GPU Image (CUDA):**
  ```sh
  make docker-run-cuda
  # or manually:
  docker run --rm -it --gpus all -p 8000:8000 ghcr.io/habedi/omni-lpr:cuda
  ```

---

### API Documentation

Omni-LPR provides two distinct APIs to access its functionality.

> [!NOTE]
> This project does not provide interactive API documentation (e.g., Swagger UI or ReDoc).
> This `README` and the `GET /api/tools` endpoint are the primary sources of API documentation.

#### 1. REST API

The REST API provides simple endpoints for recognition tasks. All tool endpoints are available under the `/api/` prefix.

##### Discovering Tools

To get a list of available tools and their input schemas, send a `GET` request to the `/api/tools` endpoint.

```sh
curl http://localhost:8000/api/tools
```

This will return a JSON array of tool objects, each with a `name`, `description`, and `input_schema`.

##### Calling a Tool

To call a specific tool, send a `POST` request to the corresponding endpoint (e.g., `/api/detect_and_recognize_plate`).
The request body must be a JSON object matching the tool's `input_schema`.

###### Example

To recognize a plate, `POST` a JSON payload with a Base64-encoded image to the `/api/detect_and_recognize_plate`
endpoint.

```sh
# Encode your image to Base64
# On macOS: base64 -i /path/to/your/image.jpg | pbcopy
# On Linux: base64 /path/to/your/image.jpg | xsel -ib

curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"image_base64": "PASTE_YOUR_BASE64_STRING_HERE"}' \
  http://localhost:8000/api/detect_and_recognize_plate
```

#### 2. MCP API (for AI Agents)

The server also exposes its capabilities as tools over the Model Context Protocol (MCP).
The MCP endpoint is available at [http://127.0.0.1:8000/mcp/sse](http://127.0.0.1:8000/mcp/sse).

##### Implemented Tools

Currently, the following tools are implemented:

* **`recognize_plate`**: Recognizes text from a pre-cropped image of a license plate.
* **`recognize_plate_from_path`**: Recognizes text from a pre-cropped license plate image located at a given URL or
  local file path.
* **`detect_and_recognize_plate`**: Detects and recognizes all license plates in a full image.
* **`detect_and_recognize_plate_from_path`**: Detects and recognizes license plates from an image at a given URL or
  local file path.
* **`list_models`**: Lists the available detector and OCR models.

<div align="center">
  <picture>
<img src="docs/assets/screenshots/mcp-inspector-1.png" alt="MCP Inspector Screenshot" width="auto" height="auto">
</picture>
</div>

-----

### Configuration

The server is configured using environment variables that can be loaded from a `.env` file if present.

| Argument              | Env Var             | Description                                                                                                                         |
|-----------------------|---------------------|-------------------------------------------------------------------------------------------------------------------------------------|
| `--port`              | `PORT`              | Server port (default: `8000`)                                                                                                       |
| `--host`              | `HOST`              | Server host (default: `127.0.0.1`)                                                                                                  |
| `--transport`         | `TRANSPORT`         | Transport protocol (default: `stdio`). Valid values are `stdio` and `sse`                                                           |
| `--log-level`         | `LOG_LEVEL`         | Logging level (default: `INFO`). Valid values are `DEBUG`, `INFO`, `WARN`, and `ERROR`                                              |
| `--default-ocr-model` | `DEFAULT_OCR_MODEL` | Default OCR model to use (default: `cct-xs-v1-global-model`). Valid values are `cct-xs-v1-global-model` and `cct-s-v1-global-model` |  

> [!NOTE]
> The REST API is only available when `TRANSPORT` is set to `sse`.
> The MCP API is available for both `stdio` (in-process) and `sse` (http) transports.

-----

### Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for details on how to make a contribution.

### License

Omni-LPR is licensed under the MIT License (see [LICENSE](LICENSE)).

### Acknowledgements

- This project uses the awesome [fast-plate-ocr](https://github.com/ankandrew/fast-plate-ocr)
  and [fast-alpr](https://github.com/ankandrew/fast-alpr) Python libraries.
- The project logo is from [SVG Repo](https://www.svgrepo.com/svg/237124/license-plate-number).
