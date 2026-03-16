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
    return BuilderConfig(prompt="Build a todo app", project_type=ProjectType.WEB_APP, rounds=3)


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
