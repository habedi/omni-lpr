## MCP Server Template

<div align="center">
  <picture>
    <img alt="Project Logo" src="docs/assets/images/logo.svg" height="25%" width="25%">
  </picture>
</div>

[![Tests](https://img.shields.io/github/actions/workflow/status/habedi/template-mcp-server/tests.yml?label=tests&style=flat&labelColor=333333&logo=github&logoColor=white)](https://github.com/habedi/template-mcp-server/actions/workflows/tests.yml)
[![Code Coverage](https://img.shields.io/codecov/c/github/habedi/template-mcp-server?style=flat&label=coverage&labelColor=333333&logo=codecov&logoColor=white)](https://codecov.io/gh/habedi/template-mcp-server)
[![Code Quality](https://img.shields.io/codefactor/grade/github/habedi/template-mcp-server?style=flat&label=code%20quality&labelColor=333333&logo=codefactor&logoColor=white)](https://www.codefactor.io/repository/github/habedi/template-mcp-server)
[![Python Version](https://img.shields.io/badge/python-%3E=3.10-3776ab?style=flat&labelColor=333333&logo=python&logoColor=white)](https://github.com/habedi/template-mcp-server)
[![License](https://img.shields.io/badge/license-MIT-00acc1?style=flat&labelColor=333333&logo=open-source-initiative&logoColor=white)](https://github.com/habedi/template-mcp-server/blob/main/LICENSE)

---

This is a template repository for creating new [Model Context Protocol](https://modelcontextprotocol.io/overview)
(MCP) servers in Python.
It includes a basic structure, a dummy Python package, unit tests, and GitHub Actions workflows for testing and
deployment.
I am sharing this template in case others find it useful.

### Features

- **Poetry**: for dependency management, packaging, publishing, etc.
- **Makefile**: for managing common tasks like testing, linting, and formatting.
- **GitHub Actions**: for running tests, linting, and deploying to PyPI.
- **Badges**: for showing the status of tests, code quality, version, etc.
- **Default files**: for configuration, testing, and documentation, like `.gitignore`, `README.md`, `LICENSE`, etc.

---

### Getting Started

#### Prerequisites

* Python (\>=3.10)
* Poetry
* GNU Make

#### Installation Steps

1. **Create a repository** from this template.
2. **Clone the repository:**
   ```sh
   git clone https://github.com/your-username/your-repository-name.git
   cd your-repository-name
   ```
3. **Install dependencies:**
   ```sh
   make setup # Install system dependencies (works on Debian/Ubuntu)
   make install # Install Python dependencies using Poetry
   ```
4. **Configure environment:**
   Copy the example environment file. The server will load variables from `.env`.
   ```sh
   cp env.example .env
   ```
5. **Run the server:**
   ```sh
   make run
   ```
   or using Poetry directly with custom environment variables:
   ```sh
   LOG_LEVEL=DEBUG HOST=0.0.0 PORT=8000 TRANSPORT=sse poetry run mcp-server
   ```
   The server will be running on `http://0.0.0.0:8000`.

#### Client Configuration

To connect a client like GitHub Copilot, add the server configuration to `~/.config/github-copilot/mcp.json`.

<details>
<summary>Click to view mcp.json example</summary>

```json
{
    "servers": {
        "template-mcp-server-network": {
            "type": "sse",
            "url": "http://localhost:8000/sse"
        }
    }
}
```

</details>

#### Interactive Client

The project includes an interactive client for testing.

1. **Run the client:**
   ```sh
   poetry run python examples/interactive_client.py
   ```
2. **Interact with the server:**
   ```
   mcp> list
   Available tools:
   - fetch: Fetches a website and returns its content

   mcp> call fetch {"url": "https://time.ir"}
   Result:
   <!DOCTYPE html>
   ...
   ```

#### Debugging

Use the [MCP Inspector](https://www.npmjs.com/package/@modelcontextprotocol/inspector) to debug messages.

```sh
npx @modelcontextprotocol/inspector poetry run mcp-server
```

#### Docker

The template is configured for containerized deployment.

* **Build the Docker Image:**
  ```sh
  make docker-build
  ```
* **Run the Docker Container:**
  ```sh
  make docker-run
  ```

#### Configuration

The server is configured using environment variables, loaded from a `.env` file.

| Variable    | Description                            | Default   |
|-------------|----------------------------------------|-----------|
| `TRANSPORT` | Transport protocol (`sse` or `stdio`). | `sse`     |
| `PORT`      | Port for the `sse` server.             | `8000`    |
| `HOST`      | Host for the `sse` server.             | `0.0.0.0` |
| `LOG_LEVEL` | Application logging level.             | `INFO`    |

---

### Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for details on how to make a contribution.

### License

This template is licensed under the MIT License ([LICENSE](LICENSE) or https://opensource.org/licenses/MIT).

### Acknowledgements

* Logo is from [SVG Repo](https://www.svgrepo.com/svg/396603/hammer-and-wrench).
