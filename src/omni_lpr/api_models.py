# src/omni_lpr/api_models.py

from pydantic import BaseModel, Field
from typing import Any, List, Optional


# A developer-friendly version of an MCP ContentBlock for JSON responses
class JsonContentBlock(BaseModel):
    """A container for structured JSON data in a response."""

    type: str = Field("json", description="The type of the content block.")
    data: Any = Field(..., description="The structured JSON payload.")


class ToolResponse(BaseModel):
    """Defines the successful response structure for a tool invocation."""

    content: List[JsonContentBlock] = Field(
        ..., description="A list of content blocks containing the tool's output."
    )


# Models for structured, machine-readable error responses
class ErrorDetail(BaseModel):
    """Provides specific details about a validation error."""

    loc: List[str] = Field(..., description="The location of the error (e.g., the field name).")
    msg: str = Field(..., description="A human-readable message for the specific error.")
    type: str = Field(..., description="The type of the error.")


class ErrorBody(BaseModel):
    """The main error object containing codes and messages."""

    code: str = Field(
        ..., description="A unique code for the error type (e.g., 'VALIDATION_ERROR')."
    )
    message: str = Field(..., description="A high-level, human-readable error message.")
    details: Optional[List[ErrorDetail]] = Field(
        None, description="Optional list of specific validation errors."
    )


class ErrorResponse(BaseModel):
    """The top-level structure for all API error responses."""

    error: ErrorBody


# Model for listing tools
class ToolDefinition(BaseModel):
    """Represents the definition of a single tool."""

    name: str
    title: str
    description: str
    inputSchema: dict


class ToolListResponse(BaseModel):
    """The response model for listing all available tools."""

    tools: List[ToolDefinition]
