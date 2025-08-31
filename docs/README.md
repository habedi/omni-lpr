## Documentation

This document provides detailed information about installing, configuring, and using Omni-LPR. For a quick start, please
see the main [README.md](../README.md) file.

### Installation

You can run Omni-LPR either by installing it as a Python library or by using a pre-built Docker image.

#### Python Installation

You can install Omni-LPR via `pip`. By default, this will use the CPU-optimized ONNX models.

```sh
pip install omni-lpr
```

For hardware-specific optimizations, you can install optional dependencies:

- **OpenVINO (Intel CPUs):** `pip install omni-lpr[openvino]`
- **CUDA (NVIDIA GPUs):** `pip install omni-lpr[cuda]`

#### Docker Installation

Pre-built Docker images are available from the [GitHub Container Registry](https://github.com/habedi/omni-lpr/packages).
You can pull the images and run them directly.

- **CPU Image (ONNX):**
  ```sh
  docker run --rm -it -p 8000:8000 ghcr.io/habedi/omni-lpr-cpu:latest
  ```

- **CPU Image (OpenVINO):**
  ```sh
  docker run --rm -it -p 8000:8000 ghcr.io/habedi/omni-lpr-openvino:latest
  ```

- **GPU Image (CUDA):**
  ```sh
  docker run --rm -it --gpus all -p 8000:8000 ghcr.io/habedi/omni-lpr-cuda:latest
  ```

> [!NOTE]
> The `latest` tag refers to the latest stable release. You can replace `latest` with a specific version tag (e.g.,
`0.2.0`) from the [list of available packages](https://github.com/habedi/omni-lpr/packages).

For developers, you can also build the Docker images locally using the provided [Makefile](../Makefile).

- **CPU (default):** `make docker-build-cpu`
- **OpenVINO:** `make docker-build-openvino`
- **CUDA:** `make docker-build-cuda`

### API Documentation

The server exposes its functionality via two interfaces: a REST API and the Model Context Protocol (MCP). Additionally,
a health check endpoint is available at `GET /api/health`, and a Prometheus metrics endpoint is at `GET /api/metrics`.

#### REST API

The REST API provides a simple way to interact with the server using standard HTTP requests. All tool endpoints are
available under the `/api/v1` prefix.

> [!TIP]
> This project provides interactive API documentation (Swagger UI and ReDoc). Once the server is running, you can access
> them at:
> - **Swagger UI**: [http://127.0.0.1:8000/apidoc/swagger](http://127.0.0.1:8000/apidoc/swagger)
> - **ReDoc**: [http://127.0.0.1:8000/apidoc/redoc](http://127.0.0.1:8000/apidoc/redoc)

##### Discovering Tools

To get a list of available tools and their input schemas, send a `GET` request to the `/api/v1/tools` endpoint.

```sh
curl http://localhost:8000/api/v1/tools
```

This will return a JSON array of tool objects, each with a `name`, `description`, and `input_schema`.

##### Calling a Tool

To call a specific tool, send a `POST` request to the `/api/v1/tools/{tool_name}/invoke` endpoint. The request body must
be a JSON object matching the tool's `input_schema`.

The tool can accept an image in three ways:

1. A Base64-encoded string in the `image_base64` field.
2. A local file path or a URL in the `path` field.
3. As a file upload (`multipart/form-data`).

###### Example: Calling `recognize_plate` with different inputs

**Using Base64:**

```sh
# On macOS: base64 -i /path/to/your/image.jpg | pbcopy
# On Linux: base64 /path/to/your/image.jpg | xsel -ib

curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"image_base64": "PASTE_YOUR_BASE64_STRING_HERE"}' \
  http://localhost:8000/api/v1/tools/recognize_plate/invoke
```

**Using a file path or URL:**

```sh
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"path": "/path/to/your/image.jpg"}' \
  http://localhost:8000/api/v1/tools/recognize_plate_from_path/invoke
```

**Using a file upload:**

```sh
curl -X POST \
  -F "image=@/path/to/your/image.jpg" \
  http://localhost:8000/api/v1/tools/recognize_plate/invoke
```

#### MCP Interface

The server also exposes its capabilities as tools over the Model Context Protocol (MCP). The MCP endpoint is available
at `http://127.0.0.1:8000/mcp/sse`.

##### Available Tools

The following tools are implemented and can be called via the MCP interface:

* **`recognize_plate`**: Recognizes text from a pre-cropped image of a license plate.
* **`recognize_plate_from_path`**: Recognizes text from a pre-cropped license plate image at a given URL or local file
  path.
* **`detect_and_recognize_plate`**: Detects and recognizes all license plates in an image.
* **`detect_and_recognize_plate_from_path`**: Detects and recognizes license plates from an image at a given URL or
  local file path.
* **`list_models`**: Lists the available detector and OCR models.

### Startup Configuration

The server can be configured using command-line arguments or environment variables. Environment variables are read from
a `.env` file if it exists. Command-line arguments take precedence over environment variables.

| Argument                   | Env Var                  | Description            | Default                               |
|----------------------------|--------------------------|------------------------|---------------------------------------|
| `--port`                   | `PORT`                   | Server port            | `8000`                                |
| `--host`                   | `HOST`                   | Server host            | `127.0.0.1`                           |
| `--log-level`              | `LOG_LEVEL`              | Logging level          | `INFO`                                |
| `--default-ocr-model`      | `DEFAULT_OCR_MODEL`      | Default OCR model      | `cct-xs-v1-global-model`              |
| `--default-detector-model` | `DEFAULT_DETECTOR_MODEL` | Default detector model | `yolo-v9-t-384-license-plate-end2end` |

### Available Models

You can override the default models for a specific request by passing `detector_model` and `ocr_model` arguments in your
request.

#### Available OCR Models:

- `cct-xs-v1-global-model` (default)
- `cct-s-v1-global-model`

#### Available Detector Models:

- `yolo-v9-s-608-license-plate-end2end`
- `yolo-v9-t-640-license-plate-end2end`
- `yolo-v9-t-512-license-plate-end2end`
- `yolo-v9-t-416-license-plate-end2end`
- `yolo-v9-t-384-license-plate-end2end` (default)
- `yolo-v9-t-256-license-plate-end2end`

> [!NOTE]
> Models are from the [fast-plate-ocr](https://github.com/ankandrew/fast-plate-ocr)
> and [fast-alpr](https://github.com/ankandrew/fast-alpr) projects. Please refer to their repositories for more
> information.

### Security Considerations

- **Network Exposure:** It is recommended to run Omni-LPR in a trusted network environment. Avoid exposing the server to
  the public internet unless strictly necessary.
- **Reverse Proxy:** If you need to expose the server to the internet, use a reverse proxy (like Nginx or Caddy) to
  handle incoming requests. This allows you to terminate TLS, handle rate limiting, and provide an extra layer of
  security.
- **Authentication:** The server does not have a built-in authentication mechanism. If you need to restrict access,
  implement authentication at the reverse proxy level.
- **Input Validation:** The API uses Pydantic for input validation, which helps prevent many common injection-style
  attacks. However, always be mindful of the data you are sending.
