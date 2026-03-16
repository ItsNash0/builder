import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from builder.context import ProjectContext
from builder.models import AgentResult, BuilderConfig, PhaseStatus, ProjectType
from builder.orchestrator import Orchestrator


@pytest.fixture
def project_dir(tmp_path):
    return tmp_path


@pytest.fixture
def config():
    return BuilderConfig(prompt="Build a todo app", project_type=ProjectType.WEB_APP, rounds=2)


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
    mock_phase.run = AsyncMock(return_value=AgentResult(success=True, output="Done", token_usage=100))
    mock_phase.validate = MagicMock(return_value=(True, ""))
    mock_phase.name = "brainstorm"
    success = await orchestrator._run_phase(mock_phase, round_number=1)
    assert success is True


@pytest.mark.asyncio
async def test_run_phase_validation_failure_retries(orchestrator):
    mock_phase = MagicMock()
    mock_phase.run = AsyncMock(return_value=AgentResult(success=True, output="Done", token_usage=100))
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
    mock_phase.run = AsyncMock(return_value=AgentResult(success=True, output="Done", token_usage=100))
    mock_phase.validate = MagicMock(return_value=(False, "Always invalid"))
    mock_phase.name = "brainstorm"
    success = await orchestrator._run_phase(mock_phase, round_number=1)
    assert success is False
    assert mock_phase.run.call_count == 3


@pytest.mark.asyncio
async def test_run_phase_agent_failure(orchestrator):
    mock_phase = MagicMock()
    mock_phase.run = AsyncMock(return_value=AgentResult(success=False, output="", error="Crashed", token_usage=0))
    mock_phase.name = "brainstorm"
    success = await orchestrator._run_phase(mock_phase, round_number=1)
    assert success is False


@pytest.mark.asyncio
async def test_state_updated_after_phase(orchestrator):
    mock_phase = MagicMock()
    mock_phase.run = AsyncMock(return_value=AgentResult(success=True, output="Done", token_usage=100))
    mock_phase.validate = MagicMock(return_value=(True, ""))
    mock_phase.name = "brainstorm"
    await orchestrator._run_phase(mock_phase, round_number=1)
    state = orchestrator.context.load_state()
    assert state.rounds["1"].phases["brainstorm"] == PhaseStatus.COMPLETED
