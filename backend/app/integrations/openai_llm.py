import logging
import time
from typing import Any

from openai import AsyncOpenAI
from pydantic import BaseModel

from app.services.llm import LLMRequest, LLMResult, LLMUsage, StructuredOutput


class InvalidStructuredOutputError(RuntimeError):
    pass


class OpenAILLMService:
    """OpenAI Responses API adapter; agents depend on the LLMService protocol."""

    def __init__(self, client: AsyncOpenAI) -> None:
        self._client = client

    async def generate_structured(
        self,
        request: LLMRequest,
        output_schema: type[StructuredOutput],
    ) -> LLMResult[StructuredOutput]:
        arguments: dict[str, Any] = {
            "model": request.model,
            "instructions": request.system_prompt,
            "input": request.user_prompt,
            "max_output_tokens": request.max_output_tokens,
            "text_format": output_schema,
        }
        if request.temperature is not None:
            arguments["temperature"] = request.temperature
        if request.tools:
            arguments["tools"] = list(request.tools)

        started_at = time.perf_counter()
        logger = logging.getLogger("specforge.llm")
        try:
            response = await self._client.responses.parse(**arguments)
            output = response.output_parsed
            if not isinstance(output, BaseModel):
                raise InvalidStructuredOutputError(
                    "OpenAI returned no validated structured output."
                )
            usage = getattr(response, "usage", None)
            duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
            result = LLMResult(
                output=output,
                response_id=response.id,
                model=response.model,
                usage=LLMUsage(
                    input_tokens=getattr(usage, "input_tokens", None),
                    output_tokens=getattr(usage, "output_tokens", None),
                    total_tokens=getattr(usage, "total_tokens", None),
                ),
                duration_ms=duration_ms,
            )
            logger.info(
                "llm_execution_completed",
                extra={
                    "agent": request.agent_name,
                    "model": result.model,
                    "status": "SUCCEEDED",
                    "duration_ms": duration_ms,
                    "input_tokens": result.usage.input_tokens,
                    "output_tokens": result.usage.output_tokens,
                    "total_tokens": result.usage.total_tokens,
                    "provider_response_id": result.response_id,
                },
            )
            return result
        except Exception as error:
            logger.warning(
                "llm_execution_failed",
                extra={
                    "agent": request.agent_name,
                    "model": request.model,
                    "status": "FAILED",
                    "duration_ms": round((time.perf_counter() - started_at) * 1000, 2),
                    "error_type": type(error).__name__,
                },
            )
            raise
