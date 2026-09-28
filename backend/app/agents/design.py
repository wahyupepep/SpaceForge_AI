from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.artifacts.schemas import (
    APISpecificationContent,
    DatabaseDesignContent,
    ProcessFlowContent,
)
from app.services.llm import LLMRequest, LLMResult, LLMService


@dataclass(frozen=True)
class DesignAgentConfig:
    model: str
    max_output_tokens: int
    temperature: Optional[float] = None


class ApprovedDesignInput(BaseModel):
    project_context: dict
    requirement_baseline: dict
    approved_solution: dict
    existing_system_analysis: Optional[dict] = None
    revision_feedback: list[dict] = Field(default_factory=list)


class UIPrototypeInput(BaseModel):
    requirement_baseline: dict
    approved_solution: dict
    process_flow: dict
    revision_feedback: list[dict] = Field(default_factory=list)


class FlowDesignerOutput(ProcessFlowContent):
    @model_validator(mode="after")
    def validate_mermaid(self) -> FlowDesignerOutput:
        source = self.mermaid.strip()
        if "```" in source or not source.startswith(
            ("flowchart", "graph", "sequenceDiagram", "stateDiagram")
        ):
            raise ValueError("mermaid must contain raw Mermaid source without code fences")
        if not self.main_flow:
            raise ValueError("main_flow must contain at least one step")
        return self


class PrototypeScreenOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    filename: str
    title: str
    purpose: str
    source_html: str = Field(min_length=1)
    requirement_refs: list[str]

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, value: str) -> str:
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]*\.html", value):
            raise ValueError("filename must be a safe lowercase .html basename")
        return value

    @model_validator(mode="after")
    def validate_browser_source(self) -> PrototypeScreenOutput:
        lowered = self.source_html.lower()
        if "<html" not in lowered or "<style" not in lowered or "<script" not in lowered:
            raise ValueError(
                "prototype screen must contain HTML, inline CSS, and vanilla JavaScript"
            )
        if "<img" in lowered or 'src="http' in lowered or 'href="http' in lowered:
            raise ValueError("prototype must not use image mockups or remote assets")
        if any(
            token in lowered
            for token in (
                "http://",
                "https://",
                "data:",
                "fetch(",
                "xmlhttprequest",
                "websocket",
            )
        ):
            raise ValueError("prototype must not use remote assets or network calls")
        if not self.requirement_refs:
            raise ValueError("every screen must trace to at least one requirement")
        return self


class UIPrototypeOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str
    screens: list[PrototypeScreenOutput] = Field(min_length=1)
    interactions: list[str]
    requirement_traceability: list[str]

    @model_validator(mode="after")
    def unique_filenames(self) -> UIPrototypeOutput:
        filenames = [screen.filename for screen in self.screens]
        if len(filenames) != len(set(filenames)):
            raise ValueError("prototype filenames must be unique")
        return self


class TechnicalArchitectOutput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    database_design: DatabaseDesignContent
    api_specification: APISpecificationContent


FLOW_SYSTEM_PROMPT = "\n".join(
    (
        "You are the Flow Designer Agent for SpaceForge AI.",
        "Use the approved functional Solution and Requirement Baseline as the only authority.",
        "Create the main flow, alternative flows, exception flows, and state transitions when "
        "state is relevant. Every step must identify actor, action, outcome, and requirement refs.",
        "The mermaid field is the primary representation. Return valid raw Mermaid syntax without "
        "Markdown code fences. Keep node labels concise and safe for Mermaid parsers.",
        "Do not create UI, database, API, source implementation, or new business requirements.",
        "When revision_feedback is present, correct every cited issue without expanding scope.",
        "Return only the structured output requested by the schema.",
    )
)


UI_SYSTEM_PROMPT = "\n".join(
    (
        "You are the UI Prototype Agent for SpaceForge AI.",
        "Create a browser-openable, semi-functional prototype based only on the approved Solution, "
        "Requirement Baseline, and Process Flow.",
        "Generate one self-contained HTML file per needed screen, such as list.html, form.html, "
        "detail.html, or approval.html. Each source_html must include semantic HTML, inline CSS in "
        "a style element, and vanilla JavaScript in a script element.",
        "Use working navigation between generated filenames and functional interactions with "
        "in-memory sample data where useful. Do not use frameworks, remote assets, external links, "
        "image mockups, data URLs, network calls, or backend implementation.",
        "Every screen must include explicit requirement_refs. This is a specification prototype, "
        "not production code and not the target business application.",
        "When revision_feedback is present, correct every cited issue without expanding scope.",
        "Return only the structured output requested by the schema.",
    )
)


TECHNICAL_SYSTEM_PROMPT = "\n".join(
    (
        "You are the Technical Architect Agent for SpaceForge AI, combining Data Architect and API "
        "Analyst responsibilities.",
        "Use the approved Solution, Requirement Baseline, Project Context, and Existing System "
        "Analysis when present. Produce specifications only; never implement the target backend.",
        "Database design must specify entity, table, every field datatype, PK, FK, nullable, "
        "default, index, unique flag, relationships, audit fields, and requirement traceability. "
        "Classify each entity REUSE, ALTER, or NEW.",
        "API specification must provide method, endpoint, purpose, actor, authorization, typed "
        "request and response fields, validation, business rules, error responses, and requirement "
        "traceability. Classify endpoints REUSE, MODIFY, NEW, or DEPRECATED.",
        "Do not emit migrations, ORM models, controllers, application code, or deployment steps.",
        "When revision_feedback is present, correct every cited issue without expanding scope.",
        "Return only the structured output requested by the schema.",
    )
)


class _StructuredDesignAgent:
    name: str
    system_prompt: str
    output_schema: type[BaseModel]

    def __init__(self, llm: LLMService, config: DesignAgentConfig) -> None:
        self._llm = llm
        self._config = config

    def _request(self, payload: BaseModel) -> LLMRequest:
        return LLMRequest(
            agent_name=self.name,
            system_prompt=self.system_prompt,
            user_prompt=json.dumps(payload.model_dump(mode="json"), ensure_ascii=False),
            model=self._config.model,
            max_output_tokens=self._config.max_output_tokens,
            temperature=self._config.temperature,
        )


class FlowDesignerAgent(_StructuredDesignAgent):
    name = "FLOW_DESIGNER"
    system_prompt = FLOW_SYSTEM_PROMPT

    def build_request(self, payload: ApprovedDesignInput) -> LLMRequest:
        return self._request(payload)

    async def analyze(self, request: LLMRequest) -> LLMResult[FlowDesignerOutput]:
        return await self._llm.generate_structured(request, FlowDesignerOutput)


class UIPrototypeAgent(_StructuredDesignAgent):
    name = "UI_PROTOTYPE_AGENT"
    system_prompt = UI_SYSTEM_PROMPT

    def build_request(self, payload: UIPrototypeInput) -> LLMRequest:
        return self._request(payload)

    async def analyze(self, request: LLMRequest) -> LLMResult[UIPrototypeOutput]:
        return await self._llm.generate_structured(request, UIPrototypeOutput)


class TechnicalArchitectAgent(_StructuredDesignAgent):
    name = "TECHNICAL_ARCHITECT"
    system_prompt = TECHNICAL_SYSTEM_PROMPT

    def build_request(self, payload: ApprovedDesignInput) -> LLMRequest:
        return self._request(payload)

    async def analyze(self, request: LLMRequest) -> LLMResult[TechnicalArchitectOutput]:
        return await self._llm.generate_structured(request, TechnicalArchitectOutput)
