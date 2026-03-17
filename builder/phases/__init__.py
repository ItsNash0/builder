from builder.phases.brainstorm import BrainstormPhase
from builder.phases.research import ResearchPhase
from builder.phases.design import DesignPhase
from builder.phases.setup import SetupPhase
from builder.phases.build import BuildPhase
from builder.phases.test import TestPhase
from builder.phases.verify import VerifyPhase
from builder.phases.improve import ImprovePhase

PHASE_CLASSES = {
    "brainstorm": BrainstormPhase,
    "research": ResearchPhase,
    "design": DesignPhase,
    "setup": SetupPhase,
    "build": BuildPhase,
    "test": TestPhase,
    "verify": VerifyPhase,
    "improve": ImprovePhase,
}

__all__ = ["PHASE_CLASSES"]
