from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field


class ChatIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: Annotated[
        str,
        Field(
            min_length=1,
            max_length=4000,
            description="User's natural-language question, e.g. 'Which AWS invoices are overdue?'",
        ),
    ]


class ToolCallTrace(BaseModel):
    name: str
    arguments: dict[str, Any]
    result: dict[str, Any]
    error: str | None = None


class ChatOut(BaseModel):
    answer: str
    tool_calls: list[ToolCallTrace] = Field(default_factory=list)
    steps: int = Field(ge=0, description="Agent loop iterations used")
