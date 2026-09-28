from enum import Enum


class ProjectType(str, Enum):
    NEW_SYSTEM = "NEW_SYSTEM"
    NEW_FEATURE = "NEW_FEATURE"
    ENHANCEMENT = "ENHANCEMENT"


class ProjectStatus(str, Enum):
    DRAFT = "DRAFT"
    CONTEXT_INCOMPLETE = "CONTEXT_INCOMPLETE"
    READY_FOR_ANALYSIS = "READY_FOR_ANALYSIS"


ENHANCEMENT_REQUIRED_CONTEXT_FIELDS = (
    "current_flow",
    "current_actors",
    "current_rules",
    "current_problem",
    "requested_change",
)


def missing_enhancement_context(context: object) -> list[str]:
    return [
        field
        for field in ENHANCEMENT_REQUIRED_CONTEXT_FIELDS
        if not str(getattr(context, field, "") or "").strip()
    ]
