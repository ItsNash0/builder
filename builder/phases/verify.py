from builder.models import AgentResult
from builder.phases.base import BasePhase


class VerifyPhase(BasePhase):
    name = "verify"

    async def run(self, round_number: int) -> AgentResult:
        config = self._get_agent_config(round_number)
        result = await self.agent_manager.spawn_agent(config, prompt=self._build_task_prompt(round_number), phase_name=self.name)
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
