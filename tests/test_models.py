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
