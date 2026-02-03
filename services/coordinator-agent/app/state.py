from enum import Enum

class WorkflowState(str, Enum):
    RECEIVED = "received"
    INTAKE_DONE = "intake_done"
    QUALIFIED = "qualified"
    SKILLS_DONE = "skills_done"
    RANKED = "ranked"
    AUDITED = "audited"
    FAILED = "failed"
