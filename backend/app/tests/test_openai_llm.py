from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from pydantic import BaseModel

from app.integrations.openai_llm import InvalidStructuredOutputError, OpenAILLMService
from app.services.llm import LLMRequest


class ExampleOutput(BaseModel):
    answer: str


def make_request() -> LLMRequest:
    return LLMRequest(
        agent_name="TEST_AGENT",
        system_prompt="Return a validated answer.",
        user_prompt="Analyze this input.",
        model="configured-model",
        max_output_tokens=200,
    )


@pytest.mark.asyncio
async def test_openai_adapter_returns_parsed_structured_output() -> None:
    parsed = ExampleOutput(answer="ready")
    parse = AsyncMock(
        return_value=SimpleNamespace(
            output_parsed=parsed,
            id="response-1",
            model="configured-model",
            usage=SimpleNamespace(input_tokens=10, output_tokens=3, total_tokens=13),
        )
    )
    client = SimpleNamespace(responses=SimpleNamespace(parse=parse))

    result = await OpenAILLMService(client).generate_structured(make_request(), ExampleOutput)

    assert result.output == parsed
    assert result.usage.total_tokens == 13
    assert result.duration_ms >= 0
    parse.assert_awaited_once_with(
        model="configured-model",
        instructions="Return a validated answer.",
        input="Analyze this input.",
        max_output_tokens=200,
        text_format=ExampleOutput,
    )


@pytest.mark.asyncio
async def test_openai_adapter_rejects_missing_parsed_output() -> None:
    client = SimpleNamespace(
        responses=SimpleNamespace(
            parse=AsyncMock(
                return_value=SimpleNamespace(
                    output_parsed=None,
                    id="response-2",
                    model="configured-model",
                    usage=None,
                )
            )
        )
    )

    with pytest.raises(InvalidStructuredOutputError):
        await OpenAILLMService(client).generate_structured(make_request(), ExampleOutput)


@pytest.mark.asyncio
async def test_openai_adapter_passes_configured_tools() -> None:
    parsed = ExampleOutput(answer="researched")
    parse = AsyncMock(
        return_value=SimpleNamespace(
            output_parsed=parsed,
            id="response-search",
            model="configured-model",
            usage=None,
        )
    )
    client = SimpleNamespace(responses=SimpleNamespace(parse=parse))
    request = LLMRequest(
        system_prompt="Research without choosing a solution.",
        user_prompt="Research this baseline.",
        model="configured-model",
        max_output_tokens=500,
        tools=({"type": "web_search"},),
    )

    await OpenAILLMService(client).generate_structured(request, ExampleOutput)

    parse.assert_awaited_once_with(
        model="configured-model",
        instructions="Research without choosing a solution.",
        input="Research this baseline.",
        max_output_tokens=500,
        text_format=ExampleOutput,
        tools=[{"type": "web_search"}],
    )
