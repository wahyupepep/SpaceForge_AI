from enum import Enum


class RequirementReadiness(str, Enum):
    READY = "READY"
    NEEDS_CLARIFICATION = "NEEDS_CLARIFICATION"
    BLOCKED = "BLOCKED"


class ClarificationStatus(str, Enum):
    PENDING = "PENDING"
    ANSWERED = "ANSWERED"


class AgentExecutionStatus(str, Enum):
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
