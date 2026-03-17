from builder.models import AgentConfig, AgentResult
from builder.phases.base import BasePhase


PERSONA_PROMPTS = {
    "user": (
        "\n\n## YOUR PERSONA: End User"
        "\n\nYou are testing this app as a REAL USER would. Your job:"
        "\n1. Follow the README to install and run the app"
        "\n2. Actually use every feature — click buttons, fill forms, navigate screens"
        "\n3. Check: Does it work? Is it intuitive? Any confusing behavior?"
        "\n4. Fix any critical bugs that prevent basic usage"
    ),
    "security": (
        "\n\n## YOUR PERSONA: Security Engineer"
        "\n\nYou are auditing this app for security vulnerabilities. Your job:"
        "\n1. Check for injection (SQL, XSS, command), hardcoded secrets, exposed API keys"
        "\n2. Review auth/session handling, input validation, CORS config"
        "\n3. Check dependencies for known vulnerabilities"
        "\n4. Fix any critical/high severity security issues directly"
    ),
    "quality": (
        "\n\n## YOUR PERSONA: Code Quality Engineer"
        "\n\nYou are reviewing this code for quality and maintainability. Your job:"
        "\n1. Run static analysis: `npx tsc --noEmit`, linters, type checking"
        "\n2. Check spec compliance: is every feature from the spec implemented?"
        "\n3. Verify README accuracy: do the commands actually work?"
        "\n4. Check dependencies: all declared? Pinned versions? No unused deps?"
        "\n5. Fix any critical issues directly"
    ),
}


class VerifyPhase(BasePhase):
    name = "verify"

    async def run(self, round_number: int) -> AgentResult:
        base_config = self._get_agent_config(round_number)
        task_prompt = self._build_task_prompt(round_number)

        configs = []
        prompts = []
        for persona_name, persona_prompt in PERSONA_PROMPTS.items():
            configs.append(AgentConfig(
                system_prompt=base_config.system_prompt + persona_prompt,
                context_files=base_config.context_files,
                working_directory=base_config.working_directory,
                timeout=base_config.timeout,
            ))
            prompts.append(task_prompt)

        results = await self.agent_manager.spawn_parallel(configs, prompts=prompts, phase_name=self.name)

        combined_output = []
        for (persona_name, _), result in zip(PERSONA_PROMPTS.items(), results):
            if result.success and result.output:
                combined_output.append(f"## {persona_name.title()} Review\n\n{result.output}")

        total_tokens = sum(r.token_usage for r in results)
        any_success = any(r.success for r in results)

        combined = AgentResult(
            success=any_success,
            output="\n\n---\n\n".join(combined_output),
            token_usage=total_tokens,
            error=None if any_success else "All verification agents failed",
        )
        if combined.success:
            output_path = self.context.get_phase_output_path(round_number, self.name)
            output_path.write_text(combined.output)
        return combined

    def validate(self, round_number: int) -> tuple[bool, str]:
        output_path = self.context.get_phase_output_path(round_number, self.name)
        if not output_path.exists():
            return False, f"Verification output not found at {output_path}"
        content = output_path.read_text().lower()
        if "finding" not in content and "issue" not in content and "review" not in content:
            return False, "Verification output missing findings section"
        return True, ""
