from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, Field


class ProjectType(StrEnum):
    WEB_APP = "web_app"
    CLI_TOOL = "cli_tool"
    API_BACKEND = "api_backend"
    LIBRARY = "library"
    MOBILE_APP = "mobile_app"
    OTHER = "other"


class PhaseStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED_SKIPPED = "failed_skipped"


PHASE_NAMES = ["brainstorm", "research", "build", "verify", "test", "improve"]


class AgentConfig(BaseModel):
    system_prompt: str
    context_files: list[str]
    working_directory: str
    timeout: int = Field(default=600, description="Timeout in seconds")


class AgentResult(BaseModel):
    success: bool
    output: str
    files_created: list[str] = Field(default_factory=list)
    error: str | None = None
    token_usage: int = 0


class BuilderConfig(BaseModel):
    prompt: str
    project_type: ProjectType
    rounds: int = Field(default=3, ge=1, le=10)
    existing_project: bool = False
    approve_spec: bool = False
    max_cost_usd: float | None = None
    webhook_url: str | None = None


class RoundState(BaseModel):
    phases: dict[str, PhaseStatus]


class StateData(BaseModel):
    current_round: int
    total_rounds: int
    current_phase: str
    phase_status: PhaseStatus
    retry_count: int = 0
    rounds: dict[str, RoundState] = Field(default_factory=dict)
    total_tokens: int = 0
