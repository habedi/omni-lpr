## Omni-LPR Examples

This directory contains examples of how to use the Omni-LPR server.

### Running the Examples

#### 1. Start the Server

First, make sure the server is running.
You can start the server using the following command:

```bash
poetry run omni-lpr
```

The server will then be listening on [http://127.0.0.1:8000](http://127.0.0.1:8000) by default.

#### 2. Run an Example

You can run individual examples from the `examples` (this) directory.
Each script accepts command-line arguments to specify the path to the image and the URL of the server endpoint.

For example, to run the REST API example with a specific image:

```bash
poetry run python examples/rest_simple_example.py --image-path /path/to/your/image.png
```

To see all available options for an example, use the `--help` flag:

```bash
poetry run python examples/rest_simple_example.py --help
```

#### 3. Run All Examples

Alternatively, you can run all examples for a specific API using the `make` commands from the root of the repository:

To run all REST API examples:

```bash
make example-rest
```

To run all MCP examples:

```bash
make example-mcp
```

### Example Files

| # | File                                                                                                         | Description                                              |
|---|--------------------------------------------------------------------------------------------------------------|----------------------------------------------------------|
| 1 | [rest_recognize_plate_example.py](rest_recognize_plate_example.py)                                           | REST example for `recognize_plate` (base64 image).       |
| 2 | [mcp_recognize_plate_example.py](mcp_recognize_plate_example.py)                                             | MCP example for `recognize_plate` (base64 image).        |
| 3 | [rest_recognize_plate_from_path_example.py](rest_recognize_plate_from_path_example.py)                       | REST example for `recognize_plate_from_path`.            |
| 4 | [mcp_recognize_plate_from_path_example.py](mcp_recognize_plate_from_path_example.py)                         | MCP example for `recognize_plate_from_path`.             |
| 5 | [rest_detect_and_recognize_plate_from_path_example.py](rest_detect_and_recognize_plate_from_path_example.py) | REST example for `detect_and_recognize_plate_from_path`. |
| 6 | [mcp_detect_and_recognize_plate_from_path_example.py](mcp_detect_and_recognize_plate_from_path_example.py)   | MCP example for `detect_and_recognize_plate_from_path`.  |
| 7 | [rest_list_models_example.py](rest_list_models_example.py)                                                   | REST example for `list_models`.                          |
| 8 | [mcp_list_models_example.py](mcp_list_models_example.py)                                                     | MCP example for `list_models`.                           |
| 9 | [health_check_example.py](health_check_example.py)                                                           | Example for checking the server's health status.         |
