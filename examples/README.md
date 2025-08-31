## Omni-LPR Examples

This directory contains examples of how to use the Omni-LPR server via the REST and MCP interfaces.

### Prerequisites

Before running the examples, ensure the Omni-LPR server is running.

If you have installed the package via `pip`, you can start the server with:

```bash
omni-lpr
```

If you are running from a development environment, you can use Poetry:

```bash
poetry run omni-lpr
```

The server will be available at `http://127.0.0.1:8000` by default.

### Running the Examples

The example scripts are designed to be run from the root of the repository. Each script accepts command-line arguments
to specify parameters like the image path.

For example, to run the REST API example for recognizing a plate from a file path:

```bash
# Using a pip installation
python examples/rest/recognize_plate_from_path_example.py --image-path /path/to/your/image.png

# Or from a development environment
poetry run python examples/rest/recognize_plate_from_path_example.py --image-path /path/to/your/image.png
```

To see all available options for an example, use the `--help` flag:

```bash
python examples/rest/recognize_plate_from_path_example.py --help
```

For convenience, you can also use the `make` commands from the root of the repository to run all examples for a specific
API:

- **Run all REST API examples:** `make example-rest`
- **Run all MCP examples:** `make example-mcp`

### Example Files

| #  | File                                                                                                               | Description                                                   |
|----|--------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------|
| 1  | [`rest/recognize_plate_example.py`](rest/recognize_plate_example.py)                                               | REST example for `recognize_plate` (base64 image).            |
| 2  | [`mcp/recognize_plate_example.py`](mcp/recognize_plate_example.py)                                                 | MCP example for `recognize_plate` (base64 image).             |
| 3  | [`rest/recognize_plate_from_path_example.py`](rest/recognize_plate_from_path_example.py)                           | REST example for `recognize_plate_from_path`.                 |
| 4  | [`mcp/recognize_plate_from_path_example.py`](mcp/recognize_plate_from_path_example.py)                             | MCP example for `recognize_plate_from_path`.                  |
| 5  | [`rest/detect_and_recognize_plate_from_path_example.py`](rest/detect_and_recognize_plate_from_path_example.py)     | REST example for `detect_and_recognize_plate_from_path`.      |
| 6  | [`mcp/detect_and_recognize_plate_from_path_example.py`](mcp/detect_and_recognize_plate_from_path_example.py)       | MCP example for `detect_and_recognize_plate_from_path`.       |
| 7  | [`rest/detect_and_recognize_plate_example.py`](rest/detect_and_recognize_plate_example.py)                         | REST example for `detect_and_recognize_plate` (base64 image). |
| 8  | [`rest/list_models_example.py`](rest/list_models_example.py)                                                       | REST example for `list_models`.                               |
| 9  | [`mcp/list_models_example.py`](mcp/list_models_example.py)                                                         | MCP example for `list_models`.                                |
| 10 | [`rest/recognize_plate_from_upload_example.py`](rest/recognize_plate_from_upload_example.py)                       | REST example for `recognize_plate` (file upload).             |
| 11 | [`rest/detect_and_recognize_plate_from_upload_example.py`](rest/detect_and_recognize_plate_from_upload_example.py) | REST example for `detect_and_recognize_plate` (file upload).  |
| 12 | [`rest/health_check_example.py`](rest/health_check_example.py)                                                     | Example for checking the server's health status.              |
