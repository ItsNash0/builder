from builder.models import AgentConfig, AgentResult
from builder.phases.base import BasePhase


class ResearchPhase(BasePhase):
    name = "research"

    async def run(self, round_number: int) -> AgentResult:
        base_config = self._get_agent_config(round_number)
        task_prompt = self._build_task_prompt(round_number)
        configs = [
            AgentConfig(
                system_prompt=base_config.system_prompt + "\n\nFocus on: library and dependency recommendations.",
                context_files=base_config.context_files,
                working_directory=base_config.working_directory,
                timeout=base_config.timeout,
            ),
            AgentConfig(
                system_prompt=base_config.system_prompt + "\n\nFocus on: design patterns and best practices.",
                context_files=base_config.context_files,
                working_directory=base_config.working_directory,
                timeout=base_config.timeout,
            ),
            AgentConfig(
                system_prompt=base_config.system_prompt + "\n\nFocus on: common pitfalls and gotchas.",
                context_files=base_config.context_files,
                working_directory=base_config.working_directory,
                timeout=base_config.timeout,
            ),
        ]
        prompts = [task_prompt] * len(configs)
        results = await self.agent_manager.spawn_parallel(configs, prompts=prompts, phase_name=self.name)
        combined_output = "\n\n".join(r.output for r in results if r.success and r.output)
        total_tokens = sum(r.token_usage for r in results)
        all_success = any(r.success for r in results)
        result = AgentResult(
            success=all_success,
            output=combined_output,
            token_usage=total_tokens,
            error=None if all_success else "All research agents failed",
        )
        if result.success:
            output_path = self.context.get_phase_output_path(round_number, self.name)
            output_path.write_text(result.output)
        return result

    def validate(self, round_number: int) -> tuple[bool, str]:
        output_path = self.context.get_phase_output_path(round_number, self.name)
        if not output_path.exists():
            return False, f"Research output not found at {output_path}"
        content = output_path.read_text().lower()
        if "recommend" not in content and "librar" not in content:
            return False, "Research output missing library recommendations"
        return True, ""
