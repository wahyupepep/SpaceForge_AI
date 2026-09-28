from enum import Enum


class SolutionWorkflowStatus(str, Enum):
    WAITING_USER_APPROVAL = "WAITING_USER_APPROVAL"
    REVISION_REQUESTED = "REVISION_REQUESTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class SolutionApprovalAction(str, Enum):
    APPROVE = "APPROVE"
    REQUEST_REVISION = "REQUEST_REVISION"
    REJECT = "REJECT"
