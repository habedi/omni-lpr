## Omni-LPR Examples

This directory contains examples of how to use the Omni-LPR server via its REST and MCP APIs.

### Running the Examples

#### 1. Start the Server

First, make sure the server is running in web server mode.
You can start it with the following command from the root of the repository:

```bash
TRANSPORT=sse poetry run omni-lpr
```

The server will then be listening on [http://127.0.0.1:8000](http://127.0.0.1:8000).

#### 2. Run an Example

Then, you can run any of the examples from the `examples` (this) directory.
Each example script accepts command-line arguments to specify the path to the image and the URL of the server endpoint.

For example, to run the REST API example with a specific image:

```bash
poetry run python examples/rest_simple_example.py --image-path /path/to/your/image.png
```

To see all available options for an example, use the `--help` flag:

```bash
poetry run python examples/rest_simple_example.py --help
```

### Example Files

| # | File                                             | Description                                                          |
|---|--------------------------------------------------|----------------------------------------------------------------------|
| 1 | [rest_simple_example.py](rest_simple_example.py) | Example of license plate recognition using the Omni-LPR REST API.    |
| 2 | [mcp_simple_example.py](mcp_simple_example.py)   | Example of using the Omni-LPR MCP API for license plate recognition. |
