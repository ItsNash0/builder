from builder.models import AgentResult
from builder.phases.base import BasePhase


class BuildPhase(BasePhase):
    name = "build"
    default_timeout = 1800

    async def run(self, round_number: int) -> AgentResult:
        config = self._get_agent_config(round_number)
        result = await self.agent_manager.spawn_agent(config, prompt=self._build_task_prompt(round_number), phase_name=self.name)
        return result

    def validate(self, round_number: int) -> tuple[bool, str]:
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
