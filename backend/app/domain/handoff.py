from enum import Enum


class DevelopmentWorkstream(str, Enum):
    DATABASE = "DATABASE"
    BACKEND = "BACKEND"
    FRONTEND = "FRONTEND"
    INTEGRATION = "INTEGRATION"
    QA = "QA"
    DOCUMENTATION = "DOCUMENTATION"
    GENERAL = "GENERAL"


class HandoffWorkflowStatus(str, Enum):
    TASKS_READY = "TASKS_READY"
    PACKAGE_READY = "PACKAGE_READY"


class HandoffExportFormat(str, Enum):
    JSON = "json"
    MARKDOWN = "markdown"
    TRELLO = "trello"
