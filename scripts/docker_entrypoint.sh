#!/bin/bash
# This script is the entrypoint for the Docker container.
# It ensures that any command is executed with the correct context.

# Exit immediately if a command exits with a non-zero status.
set -e

echo "Container entrypoint executing..."

# Execute the run command from the Makefile
# This starts the MCP server using the variables defined in the Makefile or environment.
make run

echo "Server process finished."
