from builder.models import AgentConfig, AgentResult
from builder.phases.base import BasePhase


class ImprovePhase(BasePhase):
    name = "improve"

    async def run(self, round_number: int) -> AgentResult:
        is_final_round = round_number == self.config.rounds
        config = self._get_agent_config(round_number)
        if is_final_round:
            config.system_prompt += (
                "\n\nThis is the FINAL round. Apply the top-priority improvements "
                "directly to the codebase instead of just listing them. "
                "After applying fixes, run any existing tests to verify nothing broke."
            )
        result = await self.agent_manager.spawn_agent(config, prompt=self._build_task_prompt(round_number))
        if result.success:
            output_path = self.context.get_phase_output_path(round_number, self.name)
            output_path.write_text(result.output)
        return result

    def validate(self, round_number: int) -> tuple[bool, str]:
        output_path = self.context.get_phase_output_path(round_number, self.name)
        if not output_path.exists():
            return False, f"Improvements output not found at {output_path}"
        content = output_path.read_text()
        has_list = any(
            line.strip().startswith(("1.", "2.", "-", "*"))
            for line in content.split("\n")
            if line.strip()
        )
        if not has_list:
            return False, "Improvements output missing prioritized list"
        return True, ""
