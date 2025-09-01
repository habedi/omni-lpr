## Documentation

This document provides detailed information about installing, configuring, and using Omni-LPR.
For a quick start, please see the main [README.md](../README.md) file.

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
  docker run --rm -it -p 8000:8000 -e EXECUTION_DEVICE=openvino ghcr.io/habedi/omni-lpr-openvino:latest
  ```

- **GPU Image (CUDA):**
  ```sh
  docker run --rm -it --gpus all -p 8000:8000 -e EXECUTION_DEVICE=cuda ghcr.io/habedi/omni-lpr-cuda:latest
  ```

> [!NOTE]
> The `latest` tag refers to the latest stable release. You can replace `latest` with a specific version tag (for
> example, `0.2.0`) from the [list of available packages](https://github.com/habedi/omni-lpr/packages).

For developers, you can also build the Docker images locally using the provided [Makefile](../Makefile).

- **CPU (default):** `make docker-build-cpu`
- **OpenVINO:** `make docker-build-openvino`
- **CUDA:** `make docker-build-cuda`

### API Documentation

The server exposes its functionality via two interfaces: a REST API and the MCP. Additionally, a health check endpoint
is available at `GET /api/health`.

#### REST API

The REST API provides a simple way to interact with the server using standard HTTP requests.
All tool endpoints are available under the `/api/v1` prefix.

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

To call a specific tool, send a `POST` request to the `/api/v1/tools/{tool_name}/invoke` endpoint.
The request body must be a JSON object matching the tool's `input_schema`.

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

The server also exposes its capabilities as tools over the MCP.
The MCP endpoint is available at http://127.0.0.1:8000/mcp/sse.

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

| Argument                   | Env Var                  | Description                                                    | Default                               |
|----------------------------|--------------------------|----------------------------------------------------------------|---------------------------------------|
| `--port`                   | `PORT`                   | Server port                                                    | `8000`                                |
| `--host`                   | `HOST`                   | Server host                                                    | `127.0.0.1`                           |
| `--log-level`              | `LOG_LEVEL`              | Logging level                                                  | `INFO`                                |
| `--execution-device`       | `EXECUTION_DEVICE`       | Device for model inference (`auto`, `cpu`, `cuda`, `openvino`) | `auto`                                |
| `--default-ocr-model`      | `DEFAULT_OCR_MODEL`      | Default OCR model                                              | `cct-xs-v1-global-model`              |
| `--default-detector-model` | `DEFAULT_DETECTOR_MODEL` | Default detector model                                         | `yolo-v9-t-384-license-plate-end2end` |

### Concurrency and Worker Configuration

Omni-LPR uses Gunicorn to manage multiple worker processes, allowing it to handle many concurrent REST API requests.
By default, the official Docker images are configured to run with 4 worker processes.

### Concurrency and Worker Configuration

Omni-LPR can be run in two ways: directly via the `omni-lpr` command, or using the official Docker images.
The way you run it affects how it handles concurrent requests and how you should configure it, especially for the
stateful MCP interface.

#### Running with Docker (Gunicorn)

The Docker images use Gunicorn as a process manager to run multiple Uvicorn workers.
This setup is ideal for production as it allows the server to handle many REST API requests in parallel.

- **Default Behavior**: By default, the Docker images start with 4 worker processes.
- **The MCP Problem**: The MCP is stateful. With multiple workers, Gunicorn may route requests for the same session to
  different processes, causing errors.
- **Solution**: If you plan to use the MCP interface, you must configure the Docker container to run with only one
  worker. You can do this by setting the `GUNICORN_WORKERS` environment variable.

**Example: Running Docker with a single worker for MCP compatibility**

```sh
docker run --rm -it --gpus all -p 8000:8000 \
  -e GUNICORN_WORKERS=1 \
  ghcr.io/habedi/omni-lpr-cpu:latest
```

If you are only using the stateless REST API, you can leave the worker count at the default of 4 (or higher) for better
performance.

### Hardware Acceleration Configuration

To use hardware acceleration (like an NVIDIA GPU or Intel's OpenVINO), you need to perform two steps:

1. **Install the correct package**: You must install `omni-lpr` with the appropriate "extra" to get the necessary
   hardware-specific libraries.
2. **Set the Execution Device**: You must set the `EXECUTION_DEVICE` environment variable when running the server to
   tell the application which backend to activate.

This two-step process guarantees that the application has the required libraries before it tries to use them.

#### Example: Using CUDA for NVIDIA GPUs

**Step 1: Install with the `[cuda]` extra**

```sh
pip install omni-lpr[cuda]
```

**Step 2: Run the server with `EXECUTION_DEVICE` set to `cuda`**

```sh
EXECUTION_DEVICE=cuda omni-lpr
```

#### Example: Using OpenVINO for Intel CPUs

**Step 1: Install with the `[openvino]` extra**

```sh
pip install omni-lpr[openvino]
```

**Step 2: Run the server with `EXECUTION_DEVICE` set to `openvino`**

```sh
EXECUTION_DEVICE=openvino omni-lpr
```

> [!NOTE]
> If you set `EXECUTION_DEVICE` to `cuda` or `openvino` without having installed the corresponding package extra, the
> application will fail to start with an error.
> This is intentional to prevent silent fallbacks to the CPU.

**Example: Forcing OpenVINO execution**

```sh
docker run --rm -it --gpus all -p 8000:8000 \
  -e EXECUTION_DEVICE=openvino \
  ghcr.io/habedi/omni-lpr-openvino:latest
```

#### Running with the `omni-lpr` Command (Uvicorn)

When you install the package via `pip` and run the `omni-lpr` command, it uses Uvicorn directly as the web server.

- **Default Behavior**: This method always runs with a single worker process.
- **MCP Compatibility**: Because it only uses one worker, this method is always compatible with the MCP interface out of
  the box. No special configuration is needed.

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
