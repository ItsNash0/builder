from builder.phases.brainstorm import BrainstormPhase
from builder.phases.research import ResearchPhase
from builder.phases.build import BuildPhase
from builder.phases.verify import VerifyPhase
from builder.phases.test import TestPhase
from builder.phases.improve import ImprovePhase

PHASE_CLASSES = {
    "brainstorm": BrainstormPhase,
    "research": ResearchPhase,
    "build": BuildPhase,
    "verify": VerifyPhase,
    "test": TestPhase,
    "improve": ImprovePhase,
}

__all__ = ["PHASE_CLASSES"]
