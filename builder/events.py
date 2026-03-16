from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Event:
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class PhaseStarted(Event):
    round_number: int = 0
    phase_name: str = ""


@dataclass
class PhaseCompleted(Event):
    round_number: int = 0
    phase_name: str = ""
    success: bool = True


@dataclass
class AgentSpawned(Event):
    agent_id: str = ""
    phase_name: str = ""
    description: str = ""


@dataclass
class AgentOutput(Event):
    agent_id: str = ""
    text: str = ""


@dataclass
class AgentFinished(Event):
    agent_id: str = ""
    success: bool = True
    token_usage: int = 0


@dataclass
class RoundStarted(Event):
    round_number: int = 0
    total_rounds: int = 0


@dataclass
class RoundCompleted(Event):
    round_number: int = 0


@dataclass
class RetryAttempt(Event):
    phase_name: str = ""
    attempt: int = 0
    max_retries: int = 3
    error: str = ""
    reason: str = ""


@dataclass
class LogMessage(Event):
    message: str = ""
    level: str = "info"


@dataclass
class TokenUpdate(Event):
    total_tokens: int = 0
    phase_tokens: int = 0


@dataclass
class CostUpdate(Event):
    total_cost_usd: float = 0.0


@dataclass
class ShutdownRequested(Event):
    pass
