# Builder Orchestrator Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an autonomous AI agent orchestrator that takes a user prompt and builds a complete software project through iterative rounds of brainstorm, research, build, verify, test, and improve phases.

**Architecture:** Pipeline orchestrator drives sequential phases per round, each spawning Claude Code subagents via `claude_code_sdk`. A Textual TUI dashboard shows real-time progress. State persists in `.builder/` for resume support.

**Tech Stack:** Python 3.11+, claude-code-sdk (claude_code_sdk), textual, InquirerPy, pydantic, asyncio

---

## File Structure

```
builder/
├── pyproject.toml                 # Package config, dependencies, entry point
├── builder/
│   ├── __init__.py                # Package version
│   ├── main.py                    # Entry point: wizard + orchestrator launch
│   ├── models.py                  # Pydantic models: AgentConfig, AgentResult, BuilderConfig, StateData
│   ├── context.py                 # ProjectContext: state.json R/W, config.json, .builder/ dir management
│   ├── __main__.py                # python -m builder support
│   ├── agents.py                  # AgentManager: spawn, parallel, retry via claude_code_sdk
│   ├── orchestrator.py            # Orchestrator: round loop, phase dispatch, git commits
│   ├── events.py                  # Event types for dashboard communication
│   ├── phases/
│   │   ├── __init__.py            # Phase registry
│   │   ├── base.py                # BasePhase ABC with run() and validate()
│   │   ├── brainstorm.py          # BrainstormPhase
│   │   ├── research.py            # ResearchPhase
│   │   ├── build.py               # BuildPhase
│   │   ├── verify.py              # VerifyPhase
│   │   ├── test.py                # TestPhase
│   │   └── improve.py             # ImprovePhase
│   ├── dashboard/
│   │   ├── __init__.py
│   │   └── app.py                 # Textual TUI app
│   └── prompts/
│       ├── brainstorm.md
│       ├── research.md
│       ├── build.md
│       ├── verify.md
│       ├── test.md
│       └── improve.md
└── tests/
    ├── __init__.py
    ├── test_models.py
    ├── test_context.py
    ├── test_agents.py
    ├── test_orchestrator.py
    └── test_phases.py
```

---

## Chunk 1: Project Scaffolding & Data Models

### Task 1: Project scaffolding

**Files:**
- Create: `pyproject.toml`
- Create: `builder/__init__.py`

- [ ] **Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "builder"
version = "0.1.0"
description = "Autonomous AI agent orchestrator that builds software projects"
requires-python = ">=3.11"
dependencies = [
    "claude-code-sdk>=0.0.20",
    "textual>=1.0.0",
    "InquirerPy>=0.3.4",
    "pydantic>=2.0.0",
]

[project.scripts]
builder = "builder.main:main"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
]
```

- [ ] **Step 2: Create builder/__init__.py**

```python
__version__ = "0.1.0"
```

- [ ] **Step 3: Create tests/__init__.py**

```python
```

- [ ] **Step 4: Install in dev mode**

Run: `cd /Users/itsnash0/Code/builder && pip install -e ".[dev]"`
Expected: Successfully installed builder and dependencies

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml builder/__init__.py tests/__init__.py
git commit -m "feat: scaffold project with pyproject.toml and dependencies"
```

### Task 2: Pydantic data models

**Files:**
- Create: `builder/models.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write failing tests for models**

```python
# tests/test_models.py
from builder.models import (
    AgentConfig,
    AgentResult,
    BuilderConfig,
    PhaseStatus,
    RoundState,
    StateData,
    ProjectType,
)


def test_agent_config_defaults():
    config = AgentConfig(
        system_prompt="You are a builder",
        context_files=[],
        working_directory="/tmp/test",
    )
    assert config.timeout == 600
    assert config.system_prompt == "You are a builder"


def test_agent_config_build_timeout():
    config = AgentConfig(
        system_prompt="Build",
        context_files=[],
        working_directory="/tmp",
        timeout=1800,
    )
    assert config.timeout == 1800


def test_agent_result_success():
    result = AgentResult(
        success=True,
        output="Done",
        files_created=["main.py"],
        error=None,
        token_usage=1000,
    )
    assert result.success is True
    assert result.files_created == ["main.py"]


def test_agent_result_failure():
    result = AgentResult(
        success=False,
        output="",
        files_created=[],
        error="Agent crashed",
        token_usage=500,
    )
    assert result.success is False
    assert result.error == "Agent crashed"


def test_builder_config():
    config = BuilderConfig(
        prompt="Build a todo app",
        project_type=ProjectType.WEB_APP,
        rounds=3,
    )
    assert config.rounds == 3
    assert config.project_type == ProjectType.WEB_APP


def test_state_data_initial():
    state = StateData(
        current_round=1,
        total_rounds=3,
        current_phase="brainstorm",
        phase_status=PhaseStatus.PENDING,
        retry_count=0,
        rounds={},
    )
    assert state.current_round == 1


def test_round_state():
    rs = RoundState(phases={
        "brainstorm": PhaseStatus.COMPLETED,
        "research": PhaseStatus.IN_PROGRESS,
        "build": PhaseStatus.PENDING,
        "verify": PhaseStatus.PENDING,
        "test": PhaseStatus.PENDING,
        "improve": PhaseStatus.PENDING,
    })
    assert rs.phases["brainstorm"] == PhaseStatus.COMPLETED


def test_phase_status_values():
    assert PhaseStatus.COMPLETED == "completed"
    assert PhaseStatus.IN_PROGRESS == "in_progress"
    assert PhaseStatus.PENDING == "pending"
    assert PhaseStatus.FAILED_SKIPPED == "failed_skipped"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/itsnash0/Code/builder && python -m pytest tests/test_models.py -v`
Expected: FAIL with ModuleNotFoundError (builder.models not found)

- [ ] **Step 3: Implement models**

```python
# builder/models.py
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/itsnash0/Code/builder && python -m pytest tests/test_models.py -v`
Expected: All 8 tests PASS

- [ ] **Step 5: Commit**

```bash
git add builder/models.py tests/test_models.py
git commit -m "feat: add pydantic data models for config, state, and agent types"
```

---

## Chunk 2: Event System & Project Context

### Task 3: Event types for dashboard communication

**Files:**
- Create: `builder/events.py`

- [ ] **Step 1: Create event types**

```python
# builder/events.py
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


@dataclass
class LogMessage(Event):
    message: str = ""
    level: str = "info"


@dataclass
class TokenUpdate(Event):
    total_tokens: int = 0
    phase_tokens: int = 0


@dataclass
class ShutdownRequested(Event):
    pass
```

- [ ] **Step 2: Commit**

```bash
git add builder/events.py
git commit -m "feat: add event types for orchestrator-dashboard communication"
```

### Task 4: Project context manager

**Files:**
- Create: `builder/context.py`
- Create: `tests/test_context.py`

- [ ] **Step 1: Write failing tests for ProjectContext**

```python
# tests/test_context.py
import json
from pathlib import Path

import pytest

from builder.context import ProjectContext
from builder.models import (
    BuilderConfig,
    PhaseStatus,
    ProjectType,
    RoundState,
    StateData,
)


@pytest.fixture
def tmp_project(tmp_path):
    return ProjectContext(project_dir=tmp_path)


@pytest.fixture
def config():
    return BuilderConfig(
        prompt="Build a todo app",
        project_type=ProjectType.WEB_APP,
        rounds=3,
    )


def test_initialize_creates_builder_dir(tmp_project, config):
    tmp_project.initialize(config)
    assert (tmp_project.builder_dir).exists()
    assert (tmp_project.builder_dir / "config.json").exists()
    assert (tmp_project.builder_dir / "state.json").exists()


def test_initialize_creates_subdirs(tmp_project, config):
    tmp_project.initialize(config)
    for subdir in ["specs", "research", "verification", "testing", "improvements", "logs"]:
        assert (tmp_project.builder_dir / subdir).exists()


def test_load_config(tmp_project, config):
    tmp_project.initialize(config)
    loaded = tmp_project.load_config()
    assert loaded.prompt == "Build a todo app"
    assert loaded.project_type == ProjectType.WEB_APP


def test_load_state(tmp_project, config):
    tmp_project.initialize(config)
    state = tmp_project.load_state()
    assert state.current_round == 1
    assert state.total_rounds == 3
    assert state.current_phase == "brainstorm"


def test_save_state(tmp_project, config):
    tmp_project.initialize(config)
    state = tmp_project.load_state()
    state.current_phase = "build"
    state.phase_status = PhaseStatus.IN_PROGRESS
    tmp_project.save_state(state)
    reloaded = tmp_project.load_state()
    assert reloaded.current_phase == "build"
    assert reloaded.phase_status == PhaseStatus.IN_PROGRESS


def test_update_phase_status(tmp_project, config):
    tmp_project.initialize(config)
    tmp_project.update_phase_status(1, "brainstorm", PhaseStatus.COMPLETED)
    state = tmp_project.load_state()
    assert state.rounds["1"].phases["brainstorm"] == PhaseStatus.COMPLETED


def test_has_previous_run_false(tmp_project):
    assert tmp_project.has_previous_run() is False


def test_has_previous_run_true(tmp_project, config):
    tmp_project.initialize(config)
    assert tmp_project.has_previous_run() is True


def test_archive_previous_run(tmp_project, config):
    tmp_project.initialize(config)
    tmp_project.archive_previous_run()
    assert not tmp_project.builder_dir.exists()
    assert (tmp_project.project_dir / ".builder.bak").exists()


def test_get_phase_output_path(tmp_project, config):
    tmp_project.initialize(config)
    path = tmp_project.get_phase_output_path(1, "brainstorm")
    assert path == tmp_project.builder_dir / "specs" / "round-1-spec.md"


def test_get_context_files_round_1(tmp_project, config):
    tmp_project.initialize(config)
    # Create a spec file
    spec_path = tmp_project.get_phase_output_path(1, "brainstorm")
    spec_path.write_text("# Spec")
    files = tmp_project.get_context_files(round_number=1, phase_name="research")
    # Should include config and spec from brainstorm
    assert any("config.json" in str(f) for f in files)
    assert any("round-1-spec.md" in str(f) for f in files)


def test_save_token_usage(tmp_project, config):
    tmp_project.initialize(config)
    tmp_project.save_token_usage({"round_1": {"brainstorm": 1000}}, total=1000)
    usage_path = tmp_project.builder_dir / "logs" / "token-usage.json"
    assert usage_path.exists()
    data = json.loads(usage_path.read_text())
    assert data["total"] == 1000
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/itsnash0/Code/builder && python -m pytest tests/test_context.py -v`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Implement ProjectContext**

```python
# builder/context.py
import json
import shutil
from pathlib import Path

from builder.models import (
    BuilderConfig,
    PhaseStatus,
    RoundState,
    StateData,
    PHASE_NAMES,
)

# Map phase names to output subdirectories and filename patterns
PHASE_OUTPUT_MAP = {
    "brainstorm": ("specs", "round-{round}-spec.md"),
    "research": ("research", "round-{round}-research.md"),
    "build": ("", ""),  # Build writes to project dir, not .builder/
    "verify": ("verification", "round-{round}-verify.md"),
    "test": ("testing", "round-{round}-results.md"),
    "improve": ("improvements", "round-{round}-improvements.md"),
}


class ProjectContext:
    def __init__(self, project_dir: Path):
        self.project_dir = Path(project_dir)
        self.builder_dir = self.project_dir / ".builder"

    def initialize(self, config: BuilderConfig) -> None:
        """Create .builder/ directory structure and initial state."""
        self.builder_dir.mkdir(exist_ok=True)
        for subdir in ["specs", "research", "verification", "testing", "improvements", "logs"]:
            (self.builder_dir / subdir).mkdir(exist_ok=True)

        # Save config
        config_path = self.builder_dir / "config.json"
        config_path.write_text(config.model_dump_json(indent=2))

        # Save initial state
        initial_state = StateData(
            current_round=1,
            total_rounds=config.rounds,
            current_phase="brainstorm",
            phase_status=PhaseStatus.PENDING,
            retry_count=0,
            rounds={},
        )
        self.save_state(initial_state)

    def has_previous_run(self) -> bool:
        return (self.builder_dir / "state.json").exists()

    def archive_previous_run(self) -> None:
        bak_dir = self.project_dir / ".builder.bak"
        if bak_dir.exists():
            shutil.rmtree(bak_dir)
        shutil.move(str(self.builder_dir), str(bak_dir))

    def load_config(self) -> BuilderConfig:
        config_path = self.builder_dir / "config.json"
        return BuilderConfig.model_validate_json(config_path.read_text())

    def load_state(self) -> StateData:
        state_path = self.builder_dir / "state.json"
        return StateData.model_validate_json(state_path.read_text())

    def save_state(self, state: StateData) -> None:
        state_path = self.builder_dir / "state.json"
        state_path.write_text(state.model_dump_json(indent=2))

    def update_phase_status(
        self, round_number: int, phase_name: str, status: PhaseStatus
    ) -> None:
        state = self.load_state()
        round_key = str(round_number)
        if round_key not in state.rounds:
            state.rounds[round_key] = RoundState(
                phases={p: PhaseStatus.PENDING for p in PHASE_NAMES}
            )
        state.rounds[round_key].phases[phase_name] = status
        state.current_phase = phase_name
        state.phase_status = status
        self.save_state(state)

    def get_phase_output_path(self, round_number: int, phase_name: str) -> Path:
        subdir, pattern = PHASE_OUTPUT_MAP[phase_name]
        if not subdir:
            return self.project_dir
        filename = pattern.format(round=round_number)
        return self.builder_dir / subdir / filename

    def get_context_files(self, round_number: int, phase_name: str) -> list[str]:
        """Get relevant context files for a phase based on what's available."""
        files = []
        config_path = self.builder_dir / "config.json"
        if config_path.exists():
            files.append(str(config_path))

        # Include outputs from earlier phases in the current round
        phase_index = PHASE_NAMES.index(phase_name)
        for prior_phase in PHASE_NAMES[:phase_index]:
            output_path = self.get_phase_output_path(round_number, prior_phase)
            if output_path.exists() and output_path.is_file():
                files.append(str(output_path))

        # Include improvements from previous round
        if round_number > 1:
            prev_improve = self.get_phase_output_path(round_number - 1, "improve")
            if prev_improve.exists() and prev_improve.is_file():
                files.append(str(prev_improve))

        return files

    def save_token_usage(
        self, breakdown: dict, total: int
    ) -> None:
        usage_path = self.builder_dir / "logs" / "token-usage.json"
        data = {"breakdown": breakdown, "total": total}
        usage_path.write_text(json.dumps(data, indent=2))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/itsnash0/Code/builder && python -m pytest tests/test_context.py -v`
Expected: All 12 tests PASS

- [ ] **Step 5: Commit**

```bash
git add builder/context.py tests/test_context.py
git commit -m "feat: add ProjectContext for state management and .builder/ directory"
```

---

## Chunk 3: Agent Manager

### Task 5: AgentManager wrapping claude_agent_sdk

**Files:**
- Create: `builder/agents.py`
- Create: `tests/test_agents.py`

- [ ] **Step 1: Write failing tests for AgentManager**

```python
# tests/test_agents.py
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from builder.agents import AgentManager
from builder.events import AgentFinished, AgentSpawned
from builder.models import AgentConfig, AgentResult


@pytest.fixture
def event_queue():
    return asyncio.Queue()


@pytest.fixture
def manager(event_queue):
    return AgentManager(event_queue=event_queue)


@pytest.fixture
def sample_config():
    return AgentConfig(
        system_prompt="You are a test agent",
        context_files=[],
        working_directory="/tmp/test",
        timeout=60,
    )


@pytest.mark.asyncio
async def test_spawn_agent_success(manager, sample_config):
    mock_messages = [
        MagicMock(
            __class__=MagicMock(__name__="AssistantMessage"),
            content=[MagicMock(text="Hello", __class__=MagicMock(__name__="TextBlock"))],
        ),
        MagicMock(
            __class__=MagicMock(__name__="ResultMessage"),
            total_cost_usd=0.01,
        ),
    ]

    async def mock_query(**kwargs):
        for msg in mock_messages:
            yield msg

    with patch("builder.agents.query", side_effect=mock_query):
        result = await manager.spawn_agent(sample_config, prompt="Test task")

    assert result.success is True
    assert "Hello" in result.output


@pytest.mark.asyncio
async def test_spawn_agent_error(manager, sample_config):
    async def mock_query(**kwargs):
        raise RuntimeError("Agent crashed")
        yield  # make it an async generator

    with patch("builder.agents.query", side_effect=mock_query):
        result = await manager.spawn_agent(sample_config, prompt="Test")

    assert result.success is False
    assert "Agent crashed" in result.error


@pytest.mark.asyncio
async def test_spawn_parallel(manager):
    configs = [
        AgentConfig(system_prompt="Agent 1", context_files=[], working_directory="/tmp"),
        AgentConfig(system_prompt="Agent 2", context_files=[], working_directory="/tmp"),
    ]

    async def mock_spawn(config, prompt=""):
        return AgentResult(success=True, output=f"Result from {config.system_prompt}", token_usage=100)

    manager.spawn_agent = AsyncMock(side_effect=mock_spawn)
    results = await manager.spawn_parallel(configs)

    assert len(results) == 2
    assert all(r.success for r in results)


@pytest.mark.asyncio
async def test_events_emitted_on_spawn(manager, sample_config, event_queue):
    async def mock_query(**kwargs):
        msg = MagicMock(__class__=MagicMock(__name__="ResultMessage"), total_cost_usd=0.01)
        yield msg

    with patch("builder.agents.query", side_effect=mock_query):
        await manager.spawn_agent(sample_config, prompt="Test")

    events = []
    while not event_queue.empty():
        events.append(await event_queue.get())

    event_types = [type(e).__name__ for e in events]
    assert "AgentSpawned" in event_types
    assert "AgentFinished" in event_types
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/itsnash0/Code/builder && python -m pytest tests/test_agents.py -v`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Implement AgentManager**

```python
# builder/agents.py
import asyncio
import uuid
from pathlib import Path

from claude_code_sdk import (
    query,
    ClaudeCodeOptions,
    AssistantMessage,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    CLINotFoundError,
    ProcessError,
)

from builder.events import (
    AgentSpawned,
    AgentOutput,
    AgentFinished,
    RetryAttempt,
    LogMessage,
)
from builder.models import AgentConfig, AgentResult


class AgentManager:
    def __init__(self, event_queue: asyncio.Queue):
        self.event_queue = event_queue

    async def _emit(self, event) -> None:
        await self.event_queue.put(event)

    async def spawn_agent(
        self, config: AgentConfig, prompt: str = ""
    ) -> AgentResult:
        """Spawn a single Claude Code subagent.

        Args:
            config: Agent configuration (system_prompt used as system prompt)
            prompt: The user-facing prompt/task (what to do). If empty, uses system_prompt.
        """
        agent_id = str(uuid.uuid4())[:8]

        await self._emit(AgentSpawned(
            agent_id=agent_id,
            phase_name="",
            description=config.system_prompt[:80],
        ))

        user_prompt = prompt if prompt else "Execute your task as described in the system prompt."
        output_parts: list[str] = []
        token_usage = 0

        options = ClaudeCodeOptions(
            system_prompt=config.system_prompt,
            cwd=Path(config.working_directory),
            permission_mode="bypassPermissions",
            max_turns=50,
        )

        try:
            async for message in query(prompt=user_prompt, options=options):
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            output_parts.append(block.text)
                            await self._emit(AgentOutput(
                                agent_id=agent_id,
                                text=block.text[:200],
                            ))
                        elif isinstance(block, ToolUseBlock):
                            await self._emit(AgentOutput(
                                agent_id=agent_id,
                                text=f"Using tool: {block.name}",
                            ))
                elif isinstance(message, ResultMessage):
                    if message.total_cost_usd:
                        # Approximate tokens from cost (rough estimate).
                        # The SDK does not expose raw token counts directly.
                        token_usage = int(message.total_cost_usd * 100000)

            result = AgentResult(
                success=True,
                output="\n".join(output_parts),
                files_created=[],
                token_usage=token_usage,
            )
        except CLINotFoundError:
            result = AgentResult(
                success=False,
                output="",
                error="Claude Code CLI not found. Please install it first.",
                token_usage=0,
            )
        except ProcessError as e:
            result = AgentResult(
                success=False,
                output="",
                error=f"Process failed with exit code: {e.exit_code}",
                token_usage=0,
            )
        except Exception as e:
            result = AgentResult(
                success=False,
                output="",
                error=str(e),
                token_usage=0,
            )

        await self._emit(AgentFinished(
            agent_id=agent_id,
            success=result.success,
            token_usage=result.token_usage,
        ))

        return result

    async def spawn_parallel(
        self, configs: list[AgentConfig], prompts: list[str] | None = None
    ) -> list[AgentResult]:
        """Spawn multiple agents concurrently."""
        if prompts is None:
            prompts = [""] * len(configs)
        tasks = [
            self.spawn_agent(config, prompt=prompt)
            for config, prompt in zip(configs, prompts)
        ]
        return await asyncio.gather(*tasks)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/itsnash0/Code/builder && python -m pytest tests/test_agents.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add builder/agents.py tests/test_agents.py
git commit -m "feat: add AgentManager wrapping claude_code_sdk"
```

---

## Chunk 4: Phase Base & Implementations

### Task 6: BasePhase abstract class

**Files:**
- Create: `builder/phases/__init__.py`
- Create: `builder/phases/base.py`

- [ ] **Step 1: Create phases/__init__.py (empty for now — populated in Task 7)**

```python
# builder/phases/__init__.py
```

- [ ] **Step 2: Create base phase**

```python
# builder/phases/base.py
import abc
from pathlib import Path

from builder.agents import AgentManager
from builder.context import ProjectContext
from builder.models import AgentConfig, AgentResult, BuilderConfig


class BasePhase(abc.ABC):
    """Abstract base class for all pipeline phases."""

    name: str = ""
    default_timeout: int = 600  # 10 minutes

    def __init__(
        self,
        context: ProjectContext,
        agent_manager: AgentManager,
        config: BuilderConfig,
    ):
        self.context = context
        self.agent_manager = agent_manager
        self.config = config

    @abc.abstractmethod
    async def run(self, round_number: int) -> AgentResult:
        """Execute this phase and return the result."""
        ...

    @abc.abstractmethod
    def validate(self, round_number: int) -> tuple[bool, str]:
        """Check minimum acceptance criteria.
        Returns (is_valid, error_message).
        """
        ...

    def _load_prompt_template(self) -> str:
        """Load the markdown prompt template for this phase."""
        prompt_path = Path(__file__).parent.parent / "prompts" / f"{self.name}.md"
        if prompt_path.exists():
            return prompt_path.read_text()
        return ""

    def _build_system_prompt(self, round_number: int) -> str:
        """Build the system prompt from the template with variable substitution."""
        template = self._load_prompt_template()
        return template.format(
            project_type=self.config.project_type.value,
            round_number=round_number,
            total_rounds=self.config.rounds,
            user_prompt=self.config.prompt,
        )

    def _build_task_prompt(self, round_number: int) -> str:
        """Build the user-facing task prompt with assembled context files."""
        parts = [f"Build the following: {self.config.prompt}"]

        context_files = self.context.get_context_files(round_number, self.name)
        for filepath in context_files:
            path = Path(filepath)
            if path.exists():
                content = path.read_text()
                parts.append(f"\n--- {path.name} ---\n{content}")

        return "\n\n".join(parts)

    def _get_agent_config(self, round_number: int) -> AgentConfig:
        return AgentConfig(
            system_prompt=self._build_system_prompt(round_number),
            context_files=self.context.get_context_files(round_number, self.name),
            working_directory=str(self.context.project_dir),
            timeout=self.default_timeout,
        )
```

- [ ] **Step 3: Commit**

```bash
git add builder/phases/__init__.py builder/phases/base.py
git commit -m "feat: add BasePhase abstract class with prompt loading and context assembly"
```

### Task 7: Implement all 6 phases

**Files:**
- Create: `builder/phases/brainstorm.py`
- Create: `builder/phases/research.py`
- Create: `builder/phases/build.py`
- Create: `builder/phases/verify.py`
- Create: `builder/phases/test.py`
- Create: `builder/phases/improve.py`
- Create: `tests/test_phases.py`

- [ ] **Step 1: Write failing tests for phases**

```python
# tests/test_phases.py
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from builder.context import ProjectContext
from builder.agents import AgentManager
from builder.models import AgentResult, BuilderConfig, ProjectType
from builder.phases.brainstorm import BrainstormPhase
from builder.phases.research import ResearchPhase
from builder.phases.build import BuildPhase
from builder.phases.verify import VerifyPhase
from builder.phases.test import TestPhase
from builder.phases.improve import ImprovePhase


@pytest.fixture
def project_dir(tmp_path):
    return tmp_path


@pytest.fixture
def config():
    return BuilderConfig(
        prompt="Build a todo app",
        project_type=ProjectType.WEB_APP,
        rounds=3,
    )


@pytest.fixture
def ctx(project_dir, config):
    ctx = ProjectContext(project_dir=project_dir)
    ctx.initialize(config)
    return ctx


@pytest.fixture
def event_queue():
    return asyncio.Queue()


@pytest.fixture
def agent_manager(event_queue):
    return AgentManager(event_queue=event_queue)


class TestBrainstormPhase:
    def test_validate_no_file(self, ctx, agent_manager, config):
        phase = BrainstormPhase(ctx, agent_manager, config)
        valid, msg = phase.validate(1)
        assert valid is False

    def test_validate_missing_sections(self, ctx, agent_manager, config):
        phase = BrainstormPhase(ctx, agent_manager, config)
        output_path = ctx.get_phase_output_path(1, "brainstorm")
        output_path.write_text("# Just a title")
        valid, msg = phase.validate(1)
        assert valid is False

    def test_validate_success(self, ctx, agent_manager, config):
        phase = BrainstormPhase(ctx, agent_manager, config)
        output_path = ctx.get_phase_output_path(1, "brainstorm")
        output_path.write_text(
            "# Spec\n## Features\n- Feature 1\n## Tech Stack\n- Python\n## File Structure\n- main.py"
        )
        valid, msg = phase.validate(1)
        assert valid is True


class TestResearchPhase:
    def test_validate_no_file(self, ctx, agent_manager, config):
        phase = ResearchPhase(ctx, agent_manager, config)
        valid, msg = phase.validate(1)
        assert valid is False

    def test_validate_success(self, ctx, agent_manager, config):
        phase = ResearchPhase(ctx, agent_manager, config)
        output_path = ctx.get_phase_output_path(1, "research")
        output_path.write_text("# Research\n## Libraries\n- flask recommended for web server")
        valid, msg = phase.validate(1)
        assert valid is True


class TestBuildPhase:
    def test_validate_no_files_created(self, ctx, agent_manager, config):
        phase = BuildPhase(ctx, agent_manager, config)
        valid, msg = phase.validate(1)
        assert valid is False

    def test_validate_success(self, ctx, agent_manager, config):
        phase = BuildPhase(ctx, agent_manager, config)
        # Create a source file in project dir
        (ctx.project_dir / "main.py").write_text("print('hello')")
        valid, msg = phase.validate(1)
        assert valid is True


class TestVerifyPhase:
    def test_validate_no_file(self, ctx, agent_manager, config):
        phase = VerifyPhase(ctx, agent_manager, config)
        valid, msg = phase.validate(1)
        assert valid is False

    def test_validate_success(self, ctx, agent_manager, config):
        phase = VerifyPhase(ctx, agent_manager, config)
        output_path = ctx.get_phase_output_path(1, "verify")
        output_path.write_text("# Verification\n## Findings\n- No critical issues")
        valid, msg = phase.validate(1)
        assert valid is True


class TestTestPhase:
    def test_validate_no_test_files(self, ctx, agent_manager, config):
        phase = TestPhase(ctx, agent_manager, config)
        valid, msg = phase.validate(1)
        assert valid is False

    def test_validate_success(self, ctx, agent_manager, config):
        phase = TestPhase(ctx, agent_manager, config)
        (ctx.project_dir / "test_main.py").write_text("def test_it(): pass")
        output_path = ctx.get_phase_output_path(1, "test")
        output_path.write_text("# Test Results\n- 1 passed")
        valid, msg = phase.validate(1)
        assert valid is True


class TestImprovePhase:
    def test_validate_no_file(self, ctx, agent_manager, config):
        phase = ImprovePhase(ctx, agent_manager, config)
        valid, msg = phase.validate(1)
        assert valid is False

    def test_validate_success(self, ctx, agent_manager, config):
        phase = ImprovePhase(ctx, agent_manager, config)
        output_path = ctx.get_phase_output_path(1, "improve")
        output_path.write_text("# Improvements\n1. Add error handling\n2. Improve tests")
        valid, msg = phase.validate(1)
        assert valid is True
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/itsnash0/Code/builder && python -m pytest tests/test_phases.py -v`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Implement BrainstormPhase**

```python
# builder/phases/brainstorm.py
from builder.models import AgentResult
from builder.phases.base import BasePhase


class BrainstormPhase(BasePhase):
    name = "brainstorm"

    async def run(self, round_number: int) -> AgentResult:
        config = self._get_agent_config(round_number)
        result = await self.agent_manager.spawn_agent(
            config,
            prompt=self._build_task_prompt(round_number),
        )

        if result.success:
            output_path = self.context.get_phase_output_path(round_number, self.name)
            output_path.write_text(result.output)

        return result

    def validate(self, round_number: int) -> tuple[bool, str]:
        output_path = self.context.get_phase_output_path(round_number, self.name)
        if not output_path.exists():
            return False, f"Brainstorm output not found at {output_path}"

        content = output_path.read_text().lower()
        required = ["feature", "tech stack", "file structure"]
        missing = [r for r in required if r not in content]
        if missing:
            return False, f"Brainstorm output missing sections: {', '.join(missing)}"

        return True, ""
```

- [ ] **Step 4: Implement ResearchPhase**

```python
# builder/phases/research.py
from builder.models import AgentConfig, AgentResult
from builder.phases.base import BasePhase


class ResearchPhase(BasePhase):
    name = "research"

    async def run(self, round_number: int) -> AgentResult:
        """Spawn parallel research agents for libraries, patterns, and gotchas."""
        base_config = self._get_agent_config(round_number)
        task_prompt = self._build_task_prompt(round_number)

        # Spawn 3 parallel research agents with focused sub-tasks
        configs = [
            AgentConfig(
                system_prompt=base_config.system_prompt + "\n\nFocus on: library and dependency recommendations.",
                context_files=base_config.context_files,
                working_directory=base_config.working_directory,
                timeout=base_config.timeout,
            ),
            AgentConfig(
                system_prompt=base_config.system_prompt + "\n\nFocus on: design patterns and best practices.",
                context_files=base_config.context_files,
                working_directory=base_config.working_directory,
                timeout=base_config.timeout,
            ),
            AgentConfig(
                system_prompt=base_config.system_prompt + "\n\nFocus on: common pitfalls and gotchas.",
                context_files=base_config.context_files,
                working_directory=base_config.working_directory,
                timeout=base_config.timeout,
            ),
        ]
        prompts = [task_prompt] * len(configs)
        results = await self.agent_manager.spawn_parallel(configs, prompts=prompts)

        # Merge results
        combined_output = "\n\n".join(r.output for r in results if r.success and r.output)
        total_tokens = sum(r.token_usage for r in results)
        all_success = any(r.success for r in results)  # At least one must succeed

        result = AgentResult(
            success=all_success,
            output=combined_output,
            token_usage=total_tokens,
            error=None if all_success else "All research agents failed",
        )

        if result.success:
            output_path = self.context.get_phase_output_path(round_number, self.name)
            output_path.write_text(result.output)

        return result

    def validate(self, round_number: int) -> tuple[bool, str]:
        output_path = self.context.get_phase_output_path(round_number, self.name)
        if not output_path.exists():
            return False, f"Research output not found at {output_path}"

        content = output_path.read_text().lower()
        if "recommend" not in content and "librar" not in content:
            return False, "Research output missing library recommendations"

        return True, ""
```

- [ ] **Step 5: Implement BuildPhase**

```python
# builder/phases/build.py
import os

from builder.models import AgentResult
from builder.phases.base import BasePhase


class BuildPhase(BasePhase):
    name = "build"
    default_timeout = 1800  # 30 minutes

    async def run(self, round_number: int) -> AgentResult:
        config = self._get_agent_config(round_number)
        result = await self.agent_manager.spawn_agent(
            config,
            prompt=self._build_task_prompt(round_number),
        )
        return result

    def validate(self, round_number: int) -> tuple[bool, str]:
        # Check that at least one source file exists in project dir
        # (excluding .builder/ and hidden files)
        source_extensions = {
            ".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css",
            ".go", ".rs", ".java", ".rb", ".php", ".swift", ".kt",
            ".c", ".cpp", ".h", ".json", ".yaml", ".yml", ".toml",
        }
        for entry in self.context.project_dir.rglob("*"):
            if ".builder" in entry.parts:
                continue
            if entry.is_file() and entry.suffix in source_extensions:
                return True, ""

        return False, "No source files found in project directory"
```

- [ ] **Step 6: Implement VerifyPhase**

```python
# builder/phases/verify.py
from builder.models import AgentResult
from builder.phases.base import BasePhase


class VerifyPhase(BasePhase):
    name = "verify"

    async def run(self, round_number: int) -> AgentResult:
        config = self._get_agent_config(round_number)
        result = await self.agent_manager.spawn_agent(
            config,
            prompt=self._build_task_prompt(round_number),
        )

        if result.success:
            output_path = self.context.get_phase_output_path(round_number, self.name)
            output_path.write_text(result.output)

        return result

    def validate(self, round_number: int) -> tuple[bool, str]:
        output_path = self.context.get_phase_output_path(round_number, self.name)
        if not output_path.exists():
            return False, f"Verification output not found at {output_path}"

        content = output_path.read_text().lower()
        if "finding" not in content and "issue" not in content and "review" not in content:
            return False, "Verification output missing findings section"

        return True, ""
```

- [ ] **Step 7: Implement TestPhase**

```python
# builder/phases/test.py
from builder.models import AgentResult
from builder.phases.base import BasePhase


class TestPhase(BasePhase):
    name = "test"

    async def run(self, round_number: int) -> AgentResult:
        config = self._get_agent_config(round_number)
        result = await self.agent_manager.spawn_agent(
            config,
            prompt=self._build_task_prompt(round_number),
        )

        if result.success:
            output_path = self.context.get_phase_output_path(round_number, self.name)
            output_path.write_text(result.output)

        return result

    def validate(self, round_number: int) -> tuple[bool, str]:
        # Check for test files
        test_patterns = ["test_*.py", "*_test.py", "*.test.js", "*.test.ts", "*.spec.js", "*.spec.ts"]
        has_tests = False
        for pattern in test_patterns:
            if list(self.context.project_dir.rglob(pattern)):
                has_tests = True
                break

        if not has_tests:
            return False, "No test files found in project directory"

        output_path = self.context.get_phase_output_path(round_number, self.name)
        if not output_path.exists():
            return False, f"Test results not found at {output_path}"

        return True, ""
```

- [ ] **Step 8: Implement ImprovePhase**

```python
# builder/phases/improve.py
from builder.models import AgentConfig, AgentResult
from builder.phases.base import BasePhase


class ImprovePhase(BasePhase):
    name = "improve"

    async def run(self, round_number: int) -> AgentResult:
        is_final_round = round_number == self.config.rounds
        config = self._get_agent_config(round_number)

        if is_final_round:
            # On final round, tell the agent to apply fixes directly
            config.system_prompt += (
                "\n\nThis is the FINAL round. Apply the top-priority improvements "
                "directly to the codebase instead of just listing them. "
                "After applying fixes, run any existing tests to verify nothing broke."
            )

        result = await self.agent_manager.spawn_agent(
            config,
            prompt=self._build_task_prompt(round_number),
        )

        if result.success:
            output_path = self.context.get_phase_output_path(round_number, self.name)
            output_path.write_text(result.output)

        return result

    def validate(self, round_number: int) -> tuple[bool, str]:
        output_path = self.context.get_phase_output_path(round_number, self.name)
        if not output_path.exists():
            return False, f"Improvements output not found at {output_path}"

        content = output_path.read_text()
        # Check for a numbered or bulleted list
        has_list = any(
            line.strip().startswith(("1.", "2.", "-", "*"))
            for line in content.split("\n")
            if line.strip()
        )
        if not has_list:
            return False, "Improvements output missing prioritized list"

        return True, ""
```

- [ ] **Step 9: Update phases/__init__.py with phase registry**

```python
# builder/phases/__init__.py
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
```

- [ ] **Step 10: Run tests to verify they pass**

Run: `cd /Users/itsnash0/Code/builder && python -m pytest tests/test_phases.py -v`
Expected: All 14 tests PASS

- [ ] **Step 11: Commit**

```bash
git add builder/phases/ tests/test_phases.py
git commit -m "feat: add all 6 phase implementations with validation"
```

---

## Chunk 5: Prompt Templates

### Task 8: Create markdown prompt templates

**Files:**
- Create: `builder/prompts/brainstorm.md`
- Create: `builder/prompts/research.md`
- Create: `builder/prompts/build.md`
- Create: `builder/prompts/verify.md`
- Create: `builder/prompts/test.md`
- Create: `builder/prompts/improve.md`

- [ ] **Step 1: Create brainstorm prompt**

```markdown
# Brainstorm Phase — Round {round_number}/{total_rounds}

You are a product architect. Your job is to take the user's idea and produce a detailed product specification.

## User Request
{user_prompt}

## Project Type
{project_type}

## Your Task

Create a comprehensive product specification with these sections:

### Features
List all features the product should have. Be specific and actionable.

### Tech Stack
Recommend the best technologies for this project type. Justify each choice briefly.

### Architecture
Describe the high-level architecture: components, data flow, and how they connect.

### File Structure
Propose a complete file/directory structure for the project.

### Implementation Notes
Any important considerations, edge cases, or gotchas the builder should know about.

Write your output as a well-structured markdown document.
```

- [ ] **Step 2: Create research prompt**

```markdown
# Research Phase — Round {round_number}/{total_rounds}

You are a technical researcher. Your job is to research the best libraries, patterns, and approaches for the project spec provided below.

## User Request
{user_prompt}

## Project Type
{project_type}

## Your Task

Research and recommend:

### Libraries
For each dependency the project needs, recommend a specific library with:
- Name and version
- Why it's the best choice
- Any gotchas or setup requirements

### Patterns
Identify best practices and design patterns relevant to this project.

### Similar Projects
If relevant, reference similar open-source projects that could inform the implementation.

### Gotchas
List common pitfalls for this type of project and how to avoid them.

Write your output as a well-structured markdown document.
```

- [ ] **Step 3: Create build prompt**

```markdown
# Build Phase — Round {round_number}/{total_rounds}

You are a senior software engineer. Your job is to build the project according to the specification and research provided.

## User Request
{user_prompt}

## Project Type
{project_type}

## Your Task

Build the complete project in the current working directory:

1. Create all necessary files and directories
2. Write clean, production-quality code
3. Follow the tech stack and architecture from the spec
4. Include proper error handling
5. Add configuration files (package.json, requirements.txt, etc.) as needed
6. Make sure the project can actually run

Write ALL code files. Do not leave placeholders or TODOs — implement everything fully.
If this is round 2+, review the improvement suggestions and apply them to the existing codebase.
```

- [ ] **Step 4: Create verify prompt**

```markdown
# Verify Phase — Round {round_number}/{total_rounds}

You are a code reviewer. Your job is to review all code in the project for correctness, security, and completeness.

## User Request
{user_prompt}

## Project Type
{project_type}

## Your Task

Review every file in the project and produce a verification report:

### Findings

For each issue found, document:
- **File**: which file has the issue
- **Severity**: Critical / High / Medium / Low
- **Issue**: what's wrong
- **Fix**: how to fix it

### Spec Compliance
Check that the implementation matches the spec. List any missing features or deviations.

### Security Review
Check for common security issues (injection, XSS, hardcoded secrets, etc.).

Write your output as a well-structured markdown document.
```

- [ ] **Step 5: Create test prompt**

```markdown
# Test Phase — Round {round_number}/{total_rounds}

You are a QA engineer. Your job is to write and run tests for the project.

## User Request
{user_prompt}

## Project Type
{project_type}

## Your Task

1. Write comprehensive tests:
   - Unit tests for core logic
   - Integration tests for component interactions
   - Use the appropriate test framework for the tech stack

2. Run the tests and capture results

3. Produce a test results report including:
   - Total tests: passed / failed / skipped
   - Any failing test details
   - Code coverage summary if available

Write test files in the project directory and produce the results report as markdown.
```

- [ ] **Step 6: Create improve prompt**

```markdown
# Improve Phase — Round {round_number}/{total_rounds}

You are a tech lead reviewing the project for improvements. You have access to the verification report and test results.

## User Request
{user_prompt}

## Project Type
{project_type}

## Your Task

Analyze the project and produce a prioritized improvement list:

1. **Critical fixes** — bugs, security issues, or broken functionality from the verification report
2. **Test failures** — any failing tests that need to be addressed
3. **Code quality** — refactoring opportunities, DRY violations, unclear naming
4. **Missing features** — anything from the original spec that wasn't fully implemented
5. **Performance** — obvious performance issues or optimization opportunities
6. **Developer experience** — documentation, setup instructions, error messages

Rank improvements by impact. Be specific about what to change and why.

Write your output as a numbered, prioritized markdown list.
```

- [ ] **Step 7: Commit**

```bash
git add builder/prompts/
git commit -m "feat: add markdown prompt templates for all 6 phases"
```

---

## Chunk 6: Orchestrator

### Task 9: Orchestrator with round loop and phase dispatch

**Files:**
- Create: `builder/orchestrator.py`
- Create: `tests/test_orchestrator.py`

- [ ] **Step 1: Write failing tests for Orchestrator**

```python
# tests/test_orchestrator.py
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from builder.context import ProjectContext
from builder.models import (
    AgentResult,
    BuilderConfig,
    PhaseStatus,
    ProjectType,
)
from builder.orchestrator import Orchestrator


@pytest.fixture
def project_dir(tmp_path):
    return tmp_path


@pytest.fixture
def config():
    return BuilderConfig(
        prompt="Build a todo app",
        project_type=ProjectType.WEB_APP,
        rounds=2,
    )


@pytest.fixture
def event_queue():
    return asyncio.Queue()


@pytest.fixture
def orchestrator(project_dir, config, event_queue):
    ctx = ProjectContext(project_dir=project_dir)
    ctx.initialize(config)
    return Orchestrator(context=ctx, config=config, event_queue=event_queue)


@pytest.mark.asyncio
async def test_run_phase_success(orchestrator):
    mock_phase = MagicMock()
    mock_phase.run = AsyncMock(return_value=AgentResult(
        success=True, output="Done", token_usage=100
    ))
    mock_phase.validate = MagicMock(return_value=(True, ""))
    mock_phase.name = "brainstorm"

    success = await orchestrator._run_phase(mock_phase, round_number=1)
    assert success is True


@pytest.mark.asyncio
async def test_run_phase_validation_failure_retries(orchestrator):
    mock_phase = MagicMock()
    mock_phase.run = AsyncMock(return_value=AgentResult(
        success=True, output="Done", token_usage=100
    ))
    mock_phase.validate = MagicMock(
        side_effect=[(False, "Missing sections"), (False, "Still missing"), (True, "")]
    )
    mock_phase.name = "brainstorm"

    success = await orchestrator._run_phase(mock_phase, round_number=1)
    assert success is True
    assert mock_phase.run.call_count == 3


@pytest.mark.asyncio
async def test_run_phase_exhausts_retries(orchestrator):
    mock_phase = MagicMock()
    mock_phase.run = AsyncMock(return_value=AgentResult(
        success=True, output="Done", token_usage=100
    ))
    mock_phase.validate = MagicMock(return_value=(False, "Always invalid"))
    mock_phase.name = "brainstorm"

    success = await orchestrator._run_phase(mock_phase, round_number=1)
    assert success is False
    assert mock_phase.run.call_count == 3


@pytest.mark.asyncio
async def test_run_phase_agent_failure(orchestrator):
    mock_phase = MagicMock()
    mock_phase.run = AsyncMock(return_value=AgentResult(
        success=False, output="", error="Crashed", token_usage=0
    ))
    mock_phase.name = "brainstorm"

    success = await orchestrator._run_phase(mock_phase, round_number=1)
    assert success is False


@pytest.mark.asyncio
async def test_state_updated_after_phase(orchestrator):
    mock_phase = MagicMock()
    mock_phase.run = AsyncMock(return_value=AgentResult(
        success=True, output="Done", token_usage=100
    ))
    mock_phase.validate = MagicMock(return_value=(True, ""))
    mock_phase.name = "brainstorm"

    await orchestrator._run_phase(mock_phase, round_number=1)

    state = orchestrator.context.load_state()
    assert state.rounds["1"].phases["brainstorm"] == PhaseStatus.COMPLETED
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /Users/itsnash0/Code/builder && python -m pytest tests/test_orchestrator.py -v`
Expected: FAIL with ModuleNotFoundError

- [ ] **Step 3: Implement Orchestrator**

```python
# builder/orchestrator.py
import asyncio
import subprocess
from pathlib import Path

from builder.agents import AgentManager
from builder.context import ProjectContext
from builder.events import (
    LogMessage,
    PhaseCompleted,
    PhaseStarted,
    RoundCompleted,
    RoundStarted,
    TokenUpdate,
)
from builder.models import (
    AgentResult,
    BuilderConfig,
    PhaseStatus,
    StateData,
    PHASE_NAMES,
)
from builder.phases import PHASE_CLASSES
from builder.phases.base import BasePhase


class Orchestrator:
    MAX_PHASE_RETRIES = 3

    def __init__(
        self,
        context: ProjectContext,
        config: BuilderConfig,
        event_queue: asyncio.Queue,
    ):
        self.context = context
        self.config = config
        self.event_queue = event_queue
        self.agent_manager = AgentManager(event_queue=event_queue)
        self.total_tokens = 0
        self.token_breakdown: dict = {}
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    async def _emit(self, event) -> None:
        await self.event_queue.put(event)

    async def run(self) -> None:
        """Run all rounds of the pipeline."""
        self._ensure_git_repo()
        state = self.context.load_state()
        start_round = state.current_round

        for round_num in range(start_round, self.config.rounds + 1):
            if self._cancelled:
                break

            await self._emit(RoundStarted(
                round_number=round_num,
                total_rounds=self.config.rounds,
            ))

            await self._run_round(round_num)

            if self._cancelled:
                break

            await self._emit(RoundCompleted(round_number=round_num))
            self._git_commit_round(round_num)

        # Save final token usage
        self.context.save_token_usage(self.token_breakdown, self.total_tokens)

        await self._emit(LogMessage(message="Build complete!"))

    async def _run_round(self, round_number: int) -> None:
        """Run all phases for a single round."""
        round_key = str(round_number)
        self.token_breakdown.setdefault(f"round_{round_number}", {})

        # Determine which phases to run (supports resume)
        state = self.context.load_state()
        phases_to_run = self._get_remaining_phases(state, round_number)

        for phase_name in phases_to_run:
            if self._cancelled:
                break

            phase_class = PHASE_CLASSES[phase_name]
            phase = phase_class(
                context=self.context,
                agent_manager=self.agent_manager,
                config=self.config,
            )

            success = await self._run_phase(phase, round_number)

            status = PhaseStatus.COMPLETED if success else PhaseStatus.FAILED_SKIPPED
            self.context.update_phase_status(round_number, phase_name, status)

        # Update state for next round
        if not self._cancelled:
            state = self.context.load_state()
            state.current_round = round_number + 1
            state.current_phase = "brainstorm"
            state.phase_status = PhaseStatus.PENDING
            state.retry_count = 0
            self.context.save_state(state)

    async def _run_phase(
        self, phase: BasePhase, round_number: int
    ) -> bool:
        """Run a single phase with validation and retries. Returns success."""
        await self._emit(PhaseStarted(
            round_number=round_number,
            phase_name=phase.name,
        ))

        self.context.update_phase_status(
            round_number, phase.name, PhaseStatus.IN_PROGRESS
        )

        for attempt in range(1, self.MAX_PHASE_RETRIES + 1):
            result = await phase.run(round_number)

            if not result.success:
                await self._emit(LogMessage(
                    message=f"{phase.name} failed: {result.error}",
                    level="error",
                ))
                await self._emit(PhaseCompleted(
                    round_number=round_number,
                    phase_name=phase.name,
                    success=False,
                ))
                return False

            self.total_tokens += result.token_usage
            self.token_breakdown.setdefault(
                f"round_{round_number}", {}
            )[phase.name] = result.token_usage
            await self._emit(TokenUpdate(
                total_tokens=self.total_tokens,
                phase_tokens=result.token_usage,
            ))

            is_valid, error_msg = phase.validate(round_number)
            if is_valid:
                await self._emit(PhaseCompleted(
                    round_number=round_number,
                    phase_name=phase.name,
                    success=True,
                ))
                return True

            await self._emit(LogMessage(
                message=f"{phase.name} validation failed (attempt {attempt}/{self.MAX_PHASE_RETRIES}): {error_msg}",
                level="warning",
            ))

        await self._emit(PhaseCompleted(
            round_number=round_number,
            phase_name=phase.name,
            success=False,
        ))
        return False

    def _get_remaining_phases(
        self, state: StateData, round_number: int
    ) -> list[str]:
        """Get phases that still need to run for this round."""
        round_key = str(round_number)
        if round_key not in state.rounds:
            return list(PHASE_NAMES)

        round_state = state.rounds[round_key]
        remaining = []
        for phase in PHASE_NAMES:
            status = round_state.phases.get(phase, PhaseStatus.PENDING)
            if status in (PhaseStatus.PENDING, PhaseStatus.IN_PROGRESS, PhaseStatus.FAILED_SKIPPED):
                remaining.append(phase)

        return remaining

    def _ensure_git_repo(self) -> None:
        git_dir = self.context.project_dir / ".git"
        if not git_dir.exists():
            subprocess.run(
                ["git", "init"],
                cwd=self.context.project_dir,
                capture_output=True,
            )

    def _git_commit_round(self, round_number: int) -> None:
        try:
            subprocess.run(
                ["git", "add", "-A"],
                cwd=self.context.project_dir,
                capture_output=True,
            )
            subprocess.run(
                ["git", "commit", "-m", f"builder: round {round_number} complete"],
                cwd=self.context.project_dir,
                capture_output=True,
            )
        except Exception:
            pass  # Non-critical, don't fail the build
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd /Users/itsnash0/Code/builder && python -m pytest tests/test_orchestrator.py -v`
Expected: All 5 tests PASS

- [ ] **Step 5: Commit**

```bash
git add builder/orchestrator.py tests/test_orchestrator.py
git commit -m "feat: add Orchestrator with round loop, phase dispatch, and git commits"
```

---

## Chunk 7: TUI Dashboard

### Task 10: Textual TUI dashboard

**Files:**
- Create: `builder/dashboard/__init__.py`
- Create: `builder/dashboard/app.py`

- [ ] **Step 1: Create dashboard/__init__.py**

```python
# builder/dashboard/__init__.py
```

- [ ] **Step 2: Implement TUI dashboard**

```python
# builder/dashboard/app.py
import asyncio
from datetime import datetime

from textual.app import App, ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Header, Footer, Static, RichLog, Label
from textual.reactive import reactive

from builder.events import (
    Event,
    PhaseStarted,
    PhaseCompleted,
    AgentSpawned,
    AgentOutput,
    AgentFinished,
    RoundStarted,
    RoundCompleted,
    RetryAttempt,
    LogMessage,
    TokenUpdate,
    ShutdownRequested,
)
from builder.models import PHASE_NAMES


PHASE_ICONS = {
    "pending": "[dim]\u25cb[/dim]",
    "in_progress": "[yellow]\u25c8[/yellow]",
    "completed": "[green]\u2713[/green]",
    "failed_skipped": "[red]\u2717[/red]",
}


class PhaseTracker(Static):
    """Displays phase checklist with status indicators."""

    phase_statuses: reactive[dict[str, str]] = reactive(
        lambda: {p: "pending" for p in PHASE_NAMES}
    )

    def render(self) -> str:
        lines = ["[bold]Phases[/bold]", ""]
        for phase in PHASE_NAMES:
            status = self.phase_statuses.get(phase, "pending")
            icon = PHASE_ICONS.get(status, PHASE_ICONS["pending"])
            label = phase.capitalize()
            lines.append(f"  {icon} {label}")
        return "\n".join(lines)


class ActiveAgents(Static):
    """Shows currently running agents."""

    agents: reactive[dict[str, str]] = reactive(dict)

    def render(self) -> str:
        lines = ["[bold]Active Agents[/bold]", ""]
        if not self.agents:
            lines.append("  [dim]No active agents[/dim]")
        else:
            for agent_id, desc in self.agents.items():
                lines.append(f"  [cyan][{agent_id}][/cyan] {desc}")
        return "\n".join(lines)


class StatusBar(Static):
    """Footer status bar with tokens and elapsed time."""

    total_tokens: reactive[int] = reactive(0)
    elapsed: reactive[str] = reactive("0:00:00")

    def render(self) -> str:
        return (
            f"Tokens: {self.total_tokens:,} | "
            f"Elapsed: {self.elapsed} | "
            f"Ctrl+C to cancel"
        )


class BuilderDashboard(App):
    """TUI dashboard for the Builder orchestrator."""

    CSS = """
    #main {
        layout: horizontal;
        height: 1fr;
    }
    #sidebar {
        width: 30;
        padding: 1;
    }
    #log-panel {
        width: 1fr;
        padding: 1;
    }
    #status-bar {
        dock: bottom;
        height: 1;
        padding: 0 1;
        background: $accent;
        color: $text;
    }
    PhaseTracker {
        height: auto;
        margin-bottom: 1;
    }
    ActiveAgents {
        height: auto;
    }
    """

    BINDINGS = [("q", "quit", "Quit")]

    def __init__(
        self,
        event_queue: asyncio.Queue,
        project_name: str = "Builder",
        total_rounds: int = 1,
    ):
        super().__init__()
        self.event_queue = event_queue
        self.project_name = project_name
        self.total_rounds = total_rounds
        self.current_round = 1
        self._active_agents: dict[str, str] = {}
        self._start_time = datetime.now()

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main"):
            with Vertical(id="sidebar"):
                yield PhaseTracker()
                yield ActiveAgents()
            with Vertical(id="log-panel"):
                yield Label(f"[bold]{self.project_name}[/bold] — Round 1/{self.total_rounds}")
                yield RichLog(highlight=True, markup=True, id="log")
        yield StatusBar(id="status-bar")

    def on_mount(self) -> None:
        self.title = f"Builder - {self.project_name}"
        self.set_interval(1.0, self._update_elapsed)
        asyncio.get_running_loop().create_task(self._consume_events())

    def _update_elapsed(self) -> None:
        delta = datetime.now() - self._start_time
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        self.query_one("#status-bar", StatusBar).elapsed = f"{hours}:{minutes:02d}:{seconds:02d}"

    async def _consume_events(self) -> None:
        while True:
            try:
                event = await asyncio.wait_for(self.event_queue.get(), timeout=0.1)
                self._handle_event(event)
            except asyncio.TimeoutError:
                continue
            except Exception:
                break

    def _handle_event(self, event: Event) -> None:
        log = self.query_one("#log", RichLog)
        ts = event.timestamp.strftime("%H:%M:%S")

        if isinstance(event, RoundStarted):
            self.current_round = event.round_number
            self.query_one(Label).update(
                f"[bold]{self.project_name}[/bold] — Round {event.round_number}/{event.total_rounds}"
            )
            log.write(f"[bold]{ts}[/bold] Round {event.round_number}/{event.total_rounds} started")
            # Reset phase tracker
            tracker = self.query_one(PhaseTracker)
            tracker.phase_statuses = {p: "pending" for p in PHASE_NAMES}

        elif isinstance(event, RoundCompleted):
            log.write(f"[bold green]{ts}[/bold green] Round {event.round_number} complete")

        elif isinstance(event, PhaseStarted):
            tracker = self.query_one(PhaseTracker)
            statuses = dict(tracker.phase_statuses)
            statuses[event.phase_name] = "in_progress"
            tracker.phase_statuses = statuses
            log.write(f"[bold]{ts}[/bold] Phase: [cyan]{event.phase_name}[/cyan] started")

        elif isinstance(event, PhaseCompleted):
            tracker = self.query_one(PhaseTracker)
            statuses = dict(tracker.phase_statuses)
            statuses[event.phase_name] = "completed" if event.success else "failed_skipped"
            tracker.phase_statuses = statuses
            status_text = "[green]complete[/green]" if event.success else "[red]failed[/red]"
            log.write(f"[bold]{ts}[/bold] Phase: [cyan]{event.phase_name}[/cyan] {status_text}")

        elif isinstance(event, AgentSpawned):
            self._active_agents[event.agent_id] = event.description
            agents_widget = self.query_one(ActiveAgents)
            agents_widget.agents = dict(self._active_agents)
            log.write(f"{ts} Spawned agent [{event.agent_id}]")

        elif isinstance(event, AgentOutput):
            log.write(f"{ts} [{event.agent_id}] {event.text[:100]}")

        elif isinstance(event, AgentFinished):
            self._active_agents.pop(event.agent_id, None)
            agents_widget = self.query_one(ActiveAgents)
            agents_widget.agents = dict(self._active_agents)

        elif isinstance(event, RetryAttempt):
            log.write(
                f"[yellow]{ts}[/yellow] Retry {event.attempt}/{event.max_retries} "
                f"for {event.phase_name}: {event.error[:80]}"
            )

        elif isinstance(event, LogMessage):
            color = {"error": "red", "warning": "yellow"}.get(event.level, "")
            if color:
                log.write(f"[{color}]{ts} {event.message}[/{color}]")
            else:
                log.write(f"{ts} {event.message}")

        elif isinstance(event, TokenUpdate):
            self.query_one("#status-bar", StatusBar).total_tokens = event.total_tokens

        elif isinstance(event, ShutdownRequested):
            log.write(f"[bold red]{ts} Shutting down...[/bold red]")
            self.exit()
```

- [ ] **Step 3: Commit**

```bash
git add builder/dashboard/
git commit -m "feat: add Textual TUI dashboard with phase tracker, agents view, and log"
```

---

## Chunk 8: CLI Wizard & Main Entry Point

### Task 11: CLI wizard and main entry point

**Files:**
- Create: `builder/main.py`

- [ ] **Step 1: Implement main.py**

```python
# builder/main.py
import asyncio
import sys
from pathlib import Path

from InquirerPy import inquirer

from builder.context import ProjectContext
from builder.dashboard.app import BuilderDashboard
from builder.events import ShutdownRequested
from builder.models import BuilderConfig, ProjectType
from builder.orchestrator import Orchestrator


PROJECT_TYPE_CHOICES = [
    {"name": "Web App", "value": ProjectType.WEB_APP},
    {"name": "CLI Tool", "value": ProjectType.CLI_TOOL},
    {"name": "API / Backend", "value": ProjectType.API_BACKEND},
    {"name": "Library / Package", "value": ProjectType.LIBRARY},
    {"name": "Mobile App", "value": ProjectType.MOBILE_APP},
    {"name": "Other", "value": ProjectType.OTHER},
]


def run_wizard() -> BuilderConfig:
    """Interactive CLI wizard to collect build parameters."""
    print("\n  Builder - Autonomous AI Agent Orchestrator\n")

    prompt_text = inquirer.text(
        message="What would you like to build?",
        validate=lambda x: len(x.strip()) > 0,
        invalid_message="Please describe what you want to build.",
    ).execute()

    project_type = inquirer.select(
        message="What type of project?",
        choices=PROJECT_TYPE_CHOICES,
    ).execute()

    rounds = inquirer.number(
        message="How many iteration rounds? (1-10)",
        default=3,
        min_allowed=1,
        max_allowed=10,
    ).execute()

    rounds = int(rounds)

    print(f"\n  Summary:")
    print(f"  Prompt:   {prompt_text}")
    print(f"  Type:     {project_type.value}")
    print(f"  Rounds:   {rounds}")
    print(f"  Note:     Multiple rounds will consume significant tokens.\n")

    confirm = inquirer.confirm(
        message="Start building?",
        default=True,
    ).execute()

    if not confirm:
        print("Cancelled.")
        sys.exit(0)

    return BuilderConfig(
        prompt=prompt_text,
        project_type=project_type,
        rounds=rounds,
    )


def check_resume(ctx: ProjectContext) -> bool | None:
    """Check for previous run and ask about resume.
    Returns True to resume, False to start fresh, None if no previous run.
    """
    if not ctx.has_previous_run():
        return None

    state = ctx.load_state()
    print(
        f"\n  Previous build detected "
        f"(Round {state.current_round}/{state.total_rounds}, "
        f"Phase: {state.current_phase})"
    )

    return inquirer.confirm(
        message="Resume previous build?",
        default=True,
    ).execute()


async def run_with_dashboard(
    orchestrator: Orchestrator,
    config: BuilderConfig,
    event_queue: asyncio.Queue,
) -> None:
    """Run orchestrator with TUI dashboard."""
    dashboard = BuilderDashboard(
        event_queue=event_queue,
        project_name=config.prompt[:50],
        total_rounds=config.rounds,
    )

    # Textual handles Ctrl+C natively. We hook into its shutdown to cancel the orchestrator.
    original_exit = dashboard.exit

    def patched_exit(*args, **kwargs):
        orchestrator.cancel()
        original_exit(*args, **kwargs)

    dashboard.exit = patched_exit

    # Run orchestrator in background task
    async def orchestrator_task():
        try:
            await orchestrator.run()
        except Exception as e:
            await event_queue.put(ShutdownRequested())
        finally:
            # Give dashboard time to display final state
            await asyncio.sleep(2)
            await event_queue.put(ShutdownRequested())

    # Start orchestrator before dashboard (dashboard blocks)
    task = asyncio.create_task(orchestrator_task())

    # Run dashboard (blocks until exit)
    await dashboard.run_async()

    # Clean up
    if not task.done():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


def main():
    project_dir = Path.cwd()
    ctx = ProjectContext(project_dir=project_dir)

    # Check for resume
    resume = check_resume(ctx)

    if resume is True:
        config = ctx.load_config()
    else:
        config = run_wizard()
        if resume is False:
            ctx.archive_previous_run()
        ctx.initialize(config)

    event_queue = asyncio.Queue()
    orchestrator = Orchestrator(
        context=ctx,
        config=config,
        event_queue=event_queue,
    )

    asyncio.run(run_with_dashboard(orchestrator, config, event_queue))


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Create builder/__main__.py for `python -m builder`**

```python
# builder/__main__.py
from builder.main import main

main()
```

- [ ] **Step 3: Verify the CLI runs (will fail if Claude Code not installed, but structure should work)**

Run: `cd /tmp && python -m builder --help 2>&1 || echo "Expected: starts wizard or shows error about Claude Code"`

Note: The actual wizard requires terminal interaction. The goal is to verify imports work.

Run: `cd /Users/itsnash0/Code/builder && python -c "from builder.main import main; print('imports OK')"`
Expected: "imports OK"

- [ ] **Step 4: Commit**

```bash
git add builder/main.py builder/__main__.py
git commit -m "feat: add CLI wizard and main entry point with dashboard integration"
```

---

## Chunk 9: Integration & Final Polish

### Task 12: Run full test suite and fix issues

- [ ] **Step 1: Run entire test suite**

Run: `cd /Users/itsnash0/Code/builder && python -m pytest tests/ -v`
Expected: All tests pass

- [ ] **Step 2: Fix any failing tests**

Address any import errors or test failures discovered.

- [ ] **Step 3: Verify package installs cleanly**

Run: `cd /Users/itsnash0/Code/builder && pip install -e ".[dev]" && python -c "import builder; print(builder.__version__)"`
Expected: "0.1.0"

- [ ] **Step 4: Verify CLI entry point**

Run: `cd /Users/itsnash0/Code/builder && python -c "from builder.main import run_wizard, check_resume; print('CLI OK')"`
Expected: "CLI OK"

- [ ] **Step 5: Final commit**

```bash
git add -A
git commit -m "chore: final integration fixes and polish"
```

### Task 13: Add .gitignore

- [ ] **Step 1: Create .gitignore**

```
__pycache__/
*.pyc
*.egg-info/
dist/
build/
.venv/
.env
.builder.bak/
```

- [ ] **Step 2: Commit**

```bash
git add .gitignore
git commit -m "chore: add .gitignore"
```
