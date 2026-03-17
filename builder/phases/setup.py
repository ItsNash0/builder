from pathlib import Path

from builder.models import AgentResult
from builder.phases.base import BasePhase


class SetupPhase(BasePhase):
    name = "setup"
    default_timeout = 900  # Setup can take a while with installs

    async def run(self, round_number: int) -> AgentResult:
        config = self._get_agent_config(round_number)
        result = await self.agent_manager.spawn_agent(config, prompt=self._build_task_prompt(round_number), phase_name=self.name)
        if result.success:
            output_path = self.context.get_phase_output_path(round_number, self.name)
            output_path.write_text(result.output)
        return result

    def validate(self, round_number: int) -> tuple[bool, str]:
        # Check that project has been scaffolded with a package manager config
        has_config = any(
            (self.context.project_dir / f).exists()
            for f in ["package.json", "pyproject.toml", "requirements.txt", "Cargo.toml"]
        )
        if not has_config:
            return False, "No package config found (package.json, pyproject.toml, etc.)"

        # Check that deps were installed
        has_deps = any(
            (self.context.project_dir / d).exists()
            for d in ["node_modules", ".venv", "venv", "__pypackages__"]
        )
        if not has_deps:
            return False, "Dependencies not installed (no node_modules or venv found)"

        # Check CLAUDE.md was created
        claude_md = self.context.project_dir / "CLAUDE.md"
        if not claude_md.exists():
            return False, "CLAUDE.md not created"

        return True, ""
