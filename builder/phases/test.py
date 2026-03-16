from builder.models import AgentResult
from builder.phases.base import BasePhase


class TestPhase(BasePhase):
    name = "test"

    async def run(self, round_number: int) -> AgentResult:
        config = self._get_agent_config(round_number)
        result = await self.agent_manager.spawn_agent(config, prompt=self._build_task_prompt(round_number))
        if result.success:
            output_path = self.context.get_phase_output_path(round_number, self.name)
            output_path.write_text(result.output)
        return result

    def validate(self, round_number: int) -> tuple[bool, str]:
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
