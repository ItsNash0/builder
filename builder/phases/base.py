import abc
from pathlib import Path

from builder.agents import AgentManager
from builder.context import ProjectContext
from builder.models import AgentConfig, AgentResult, BuilderConfig


MAX_CONTEXT_CHARS = 50000  # Cap context per file to prevent prompt explosion


class BasePhase(abc.ABC):
    name: str = ""
    default_timeout: int = 600

    def __init__(self, context: ProjectContext, agent_manager: AgentManager, config: BuilderConfig):
        self.context = context
        self.agent_manager = agent_manager
        self.config = config

    @abc.abstractmethod
    async def run(self, round_number: int) -> AgentResult:
        ...

    @abc.abstractmethod
    def validate(self, round_number: int) -> tuple[bool, str]:
        ...

    def _load_prompt_template(self) -> str:
        prompt_path = Path(__file__).parent.parent / "prompts" / f"{self.name}.md"
        if prompt_path.exists():
            return prompt_path.read_text()
        return ""

    def _build_system_prompt(self, round_number: int) -> str:
        template = self._load_prompt_template()
        prompt = template.format(
            project_type=self.config.project_type.value,
            round_number=round_number,
            total_rounds=self.config.rounds,
            user_prompt=self.config.prompt,
        )
        if self.config.existing_project:
            prompt += (
                "\n\n## EXISTING PROJECT MODE"
                "\n\nThis is an EXISTING project with code already in the working directory. "
                "You MUST:"
                "\n1. First explore and understand the existing codebase (read files, check structure)"
                "\n2. Identify the tech stack, frameworks, and patterns already in use"
                "\n3. Work WITH the existing code — do not rewrite from scratch"
                "\n4. Preserve existing functionality while making improvements"
                "\n5. If the existing code doesn't work, fix it before adding anything new"
            )
        return prompt

    def _build_task_prompt(self, round_number: int) -> str:
        if self.config.existing_project:
            parts = [f"Work on the existing project: {self.config.prompt}"]
        else:
            parts = [f"Build the following: {self.config.prompt}"]
        context_files = self.context.get_context_files(round_number, self.name)
        for filepath in context_files:
            path = Path(filepath)
            if path.exists():
                content = path.read_text()
                # Cap context size to prevent prompt explosion in later rounds
                if len(content) > MAX_CONTEXT_CHARS:
                    content = content[:MAX_CONTEXT_CHARS] + "\n\n... [truncated — full output in file] ..."
                parts.append(f"\n--- {path.name} ---\n{content}")
        return "\n\n".join(parts)

    def _get_agent_config(self, round_number: int) -> AgentConfig:
        return AgentConfig(
            system_prompt=self._build_system_prompt(round_number),
            context_files=self.context.get_context_files(round_number, self.name),
            working_directory=str(self.context.project_dir),
            timeout=self.default_timeout,
        )
