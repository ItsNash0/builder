from builder.models import AgentResult
from builder.phases.base import BasePhase


class BrainstormPhase(BasePhase):
    name = "brainstorm"

    async def run(self, round_number: int) -> AgentResult:
        config = self._get_agent_config(round_number)
        result = await self.agent_manager.spawn_agent(config, prompt=self._build_task_prompt(round_number))
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
