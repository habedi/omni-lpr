from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class ErrorCode(str, Enum):
    """Enum for error codes used in Omni-LPR responses"""

    VALIDATION_ERROR = "VALIDATION_ERROR"
    DESERIALIZATION_ERROR = "DESERIALIZATION_ERROR"
    TOOL_LOGIC_ERROR = "TOOL_LOGIC_ERROR"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


class APIError(BaseModel):
    """Represents an error returned by the Omni-LPR API"""

    code: ErrorCode = Field(..., description="A unique code identifying the error type.")
    message: str = Field(..., description="A human-readable message describing the error.")
    details: Optional[Any] = Field(None, description="Optional structured details about the error.")


class ToolLogicError(Exception):
    """Custom exception for tool-related errors that can be mapped to APIError"""

    def __init__(
        self, message: str, code: ErrorCode = ErrorCode.TOOL_LOGIC_ERROR, details: Any = None
    ):
        super().__init__(message)
        self.error = APIError(code=code, message=message, details=details)
