### Getting Started

You can run Omni-LPR either by installing it as a Python library or by using a ready-to-use Docker image.

#### Method 1

You can install Omni-LPR via `pip` or any other Python package manager.

```sh
pip install omni-lpr
````

By default, the server will use the CPU-enabled ONNX models.
You can use models that are optimized for specific hardware backends by installing the optional dependencies:

- **OpenVINO (Intel CPUs):** `pip install omni-lpr[openvino]`
- **CUDA (NVIDIA GPUs):** `pip install omni-lpr[cuda]`

##### Starting the Server

To start the server, run the `omni-lpr` command:

```sh
omni-lpr --host 0.0.0.0 --port 8000
```

#### Method 2

Pre-built Docker images are available from the [GitHub Container Registry](https://github.com/habedi/omni-lpr/packages).
You can build the images locally or pull them from the registry.

##### Building the Docker Images

You can build the Docker images for different backends using the provided [Makefile](../Makefile).

- **CPU (default):** `make docker-build-cpu`
- **OpenVINO:** `make docker-build-openvino`
- **CUDA:** `make docker-build-cuda`

##### Running the Container

When you have built or pulled the images, you can run them using the following commands:

- **CPU Image (ONNX):**
  ```sh
  # Use locally built image
  make docker-run-cpu

  # Or from the GitHub Container Registry
  docker run --rm -it -p 8000:8000 ghcr.io/habedi/omni-lpr-cpu:TAG
  ```

- **CPU Image (OpenVINO):**
  ```sh
  # Use locally built image
  make docker-run-openvino

  # Or from the GitHub Container Registry
  docker run --rm -it -p 8000:8000 ghcr.io/habedi/omni-lpr-openvino:TAG
  ```

- **GPU Image (CUDA):**
  ```sh
  # Use locally built image
  make docker-run-cuda

  # Or from the GitHub Container Registry
  docker run --rm -it --gpus all -p 8000:8000 ghcr.io/habedi/omni-lpr-cuda:TAG
  ```

> [!NOTE]
> The `TAG` in the above commands is a release tag like `0.2.0` or `latest` for the latest development version.
> You can find the available tags in the [GitHub Container Registry](https://github.com/habedi/omni-lpr/packages).

---

### Documentation

The server exposes its functionality via two interfaces: REST API and MCP.
A health check endpoint is also available at `GET /api/health`.
For monitoring, a Prometheus metrics endpoint is available at `GET /api/metrics`.
It also can be configured using command-line arguments or environment variables on startup.

#### 1. REST API

The REST API provides a simple way to interact with the server using standard HTTP requests.
All tool endpoints are available under the `/api/v1` prefix.

> [!TIP]
> This project provides interactive API documentation (Swagger UI and ReDoc).
> Once the server is running, you can access them at:
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

###### Example: Calling `detect_and_recognize_plate`

To detect and recognize a plate, `POST` a JSON payload to the `/api/v1/tools/detect_and_recognize_plate/invoke`
endpoint.

**Using Base64:**

```sh
# Encode your image to Base64
# On macOS: base64 -i /path/to/your/image.jpg | pbcopy
# On Linux: base64 /path/to/your/image.jpg | xsel -ib

curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"image_base64": "PASTE_YOUR_BASE64_STRING_HERE"}' \
  http://localhost:8000/api/v1/tools/detect_and_recognize_plate/invoke
```

**Using a file path or URL:**

```sh
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"path": "/path/to/your/image.jpg"}' \
  http://localhost:8000/api/v1/tools/detect_and_recognize_plate/invoke

# Or with a URL
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"path": "https://example.com/plate.jpg"}' \
  http://localhost:8000/api/v1/tools/detect_and_recognize_plate/invoke
```

**Using a file upload:**

```sh
curl -X POST \
  -F "image=@/path/to/your/image.jpg" \
  -F "ocr_model=cct-s-v1-global-model" \
  http://localhost:8000/api/v1/tools/recognize_plate/invoke
```

#### 2. MCP Interface (for AI Agents)

The server also exposes its capabilities as tools over the Model Context Protocol (MCP).
The MCP endpoint is available at [http://127.0.0.1:8000/mcp/sse](http://127.0.0.1:8000/mcp/sse).

##### Available Tools

Currently, the following tools are implemented and can be called via the MCP interface:

* **`recognize_plate`**: Recognizes text from a pre-cropped image of a license plate.
* **`recognize_plate_from_path`**: Recognizes text from a pre-cropped license plate image located at a given URL or
  local file path.
* **`detect_and_recognize_plate`**: Detects and recognizes all license plates in a full image.
* **`detect_and_recognize_plate_from_path`**: Detects and recognizes license plates from an image at a given URL or
  local file path.
* **`list_models`**: Lists the available detector and OCR models.

The figure below shows a screenshot of the [MCP Inspector](https://github.com/modelcontextprotocol/inspector)
tool connected to the Omni-LPR server.

<div align="center">
  <picture>
<img src="assets/screenshots/mcp-inspector-2.png" alt="MCP Inspector Screenshot" width="auto" height="auto">
</picture>
</div>

#### Startup Configuration

As mentioned earlier, the server can be configured using command-line arguments or environment variables on startup.
Environment variables are read from `.env` file if it exists and from the current process environment.
Command-line arguments take precedence over environment variables.
The following table summarizes the available configuration options:

| Argument                   | Env Var                  | Description                                                                                                        |
|----------------------------|--------------------------|--------------------------------------------------------------------------------------------------------------------|
| `--port`                   | `PORT`                   | Server port (default: `8000`)                                                                                      |
| `--host`                   | `HOST`                   | Server host (default: `127.0.0.1`)                                                                                 |
| `--log-level`              | `LOG_LEVEL`              | Logging level (default: `INFO`). Valid values are `DEBUG`, `INFO`, `WARN`, `ERROR`, `CRITICAL` (case-insensitive). |
| `--default-ocr-model`      | `DEFAULT_OCR_MODEL`      | Default OCR model to use (default: `cct-xs-v1-global-model`).                                                      |
| `--default-detector-model` | `DEFAULT_DETECTOR_MODEL` | Default detector model to use (default: `yolo-v9-t-384-license-plate-end2end`).                                    |

> [!NOTE]
> The `detect_and_recognize_plate` and `detect_and_recognize_plate_from_path` tools take optional `detector_model` and
`ocr_model` arguments to override the default models for a specific request.
>
> Available OCR Models:
> - `cct-xs-v1-global-model` (default)
> - `cct-s-v1-global-model`
>
> Available Detector Models:
> - `yolo-v9-s-608-license-plate-end2end`
> - `yolo-v9-t-640-license-plate-end2end`
> - `yolo-v9-t-512-license-plate-end2end`
> - `yolo-v9-t-416-license-plate-end2end`
> - `yolo-v9-t-384-license-plate-end2end` (default)
> - `yolo-v9-t-256-license-plate-end2end`

### Security Considerations

- **Network Exposure:** It is recommended to run Omni-LPR in a trusted network environment. Avoid exposing the server to
  the public internet unless it is strictly necessary.
- **Reverse Proxy:** If you need to expose the server to the internet, it is recommended to use a reverse proxy (like
  Nginx or Caddy) to handle incoming requests. This allows you to terminate TLS, handle rate limiting, and
  provide an extra layer of security.
- **Authentication:** The server does not have a built-in authentication mechanism. If you need to restrict access to
  the API, you should implement authentication at the reverse proxy level.
- **Input Validation:** The API uses Pydantic for input validation, which helps prevent many common injection-style
  attacks. However, it is still important to be aware of the data you are sending to the server.
