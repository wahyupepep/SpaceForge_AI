from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Generic, Protocol, TypeVar

from pydantic import BaseModel

StructuredOutput = TypeVar("StructuredOutput", bound=BaseModel)


@dataclass(frozen=True)
class LLMRequest:
    system_prompt: str
    user_prompt: str
    model: str
    max_output_tokens: int
    temperature: float | None = None
    tools: tuple[dict[str, Any], ...] = ()
    agent_name: str = "UNSPECIFIED_AGENT"


@dataclass(frozen=True)
class LLMUsage:
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


@dataclass(frozen=True)
class LLMResult(Generic[StructuredOutput]):
    output: StructuredOutput
    response_id: str
    model: str
    usage: LLMUsage
    duration_ms: float = 0.0


class LLMService(Protocol):
    async def generate_structured(
        self,
        request: LLMRequest,
        output_schema: type[StructuredOutput],
    ) -> LLMResult[StructuredOutput]: ...
