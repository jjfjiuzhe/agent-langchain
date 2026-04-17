from typing import Any

from pydantic import BaseModel, Field


class TaskRequest(BaseModel):
    """User request payload for a development task analysis."""

    requirement: str = Field(..., min_length=1, description="Detailed user requirement to analyze.")
    context: dict[str, Any] = Field(default_factory=dict, description="Optional caller-provided context.")


class IngestRequest(BaseModel):
    """Request payload for indexing documents and code into PGVector."""

    docs_path: str | None = None
    code_path: str | None = None
