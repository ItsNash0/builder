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
    spec_path = tmp_project.get_phase_output_path(1, "brainstorm")
    spec_path.write_text("# Spec")
    files = tmp_project.get_context_files(round_number=1, phase_name="research")
    assert any("config.json" in str(f) for f in files)
    assert any("round-1-spec.md" in str(f) for f in files)


def test_save_token_usage(tmp_project, config):
    tmp_project.initialize(config)
    tmp_project.save_token_usage({"round_1": {"brainstorm": 1000}}, total=1000)
    usage_path = tmp_project.builder_dir / "logs" / "token-usage.json"
    assert usage_path.exists()
    data = json.loads(usage_path.read_text())
    assert data["total"] == 1000
