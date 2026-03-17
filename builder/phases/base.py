import abc
from pathlib import Path

from builder.agents import AgentManager
from builder.context import ProjectContext
from builder.error_memory import ErrorMemory
from builder.models import AgentConfig, AgentResult, BuilderConfig
from builder.repomap import generate_repo_map


MAX_CONTEXT_CHARS = 50000  # Cap context per file to prevent prompt explosion

# Phases that benefit from a repo map (codebase awareness without full files)
REPO_MAP_PHASES = {"build", "test", "verify", "improve"}

# Per-phase instructions for existing project mode
EXISTING_PROJECT_INSTRUCTIONS = {
    "brainstorm": (
        "\n\n## EXISTING PROJECT MODE — AUDIT"
        "\n\nThis is an EXISTING project. Your job is to AUDIT it, not design from scratch."
        "\n\n**Step 1: Deep exploration (DO THIS FIRST)**"
        "\n1. Read package.json / pyproject.toml / Cargo.toml for deps and scripts"
        "\n2. Read README.md, CLAUDE.md if they exist"
        "\n3. Read main entry points (app/, src/, index.*, main.*)"
        "\n4. Read config files (tsconfig, tailwind, next.config, .env.example)"
        "\n5. List all directories and key files"
        "\n\n**Step 2: Try to run it**"
        "\n1. Install deps (npm install / pip install)"
        "\n2. Try to build/compile"
        "\n3. Try to start the app"
        "\n4. Document what works and what breaks"
        "\n\n**Step 3: Produce an audit spec**"
        "\n- Current state: what works, what's broken, what errors occur"
        "\n- Tech stack: exact frameworks, versions, patterns in use (DO NOT change the stack)"
        "\n- Missing/broken features vs. what the user requested"
        "\n- Prioritized list of fixes needed"
        "\n- File structure as it currently exists"
        "\n- Keep the existing stack — do NOT suggest switching frameworks"
    ),
    "research": (
        "\n\n## EXISTING PROJECT MODE"
        "\n\nThis project already exists. Research should focus on:"
        "\n1. Latest versions of the EXISTING dependencies (check what's in package.json/pyproject.toml)"
        "\n2. Migration guides if deps are outdated"
        "\n3. Best practices for the EXISTING stack (don't suggest new stacks)"
        "\n4. Solutions for specific issues identified in the brainstorm/audit"
    ),
    "build": (
        "\n\n## EXISTING PROJECT MODE — FIX & EXTEND"
        "\n\nThis is an EXISTING project. You MUST:"
        "\n1. **Read the codebase first** — understand the architecture before changing anything"
        "\n2. **Fix broken things first** — if the app doesn't start, fix that before adding features"
        "\n3. **Follow existing patterns** — match the code style, naming, and architecture"
        "\n4. **Don't rewrite from scratch** — modify existing files, don't replace them"
        "\n5. **Don't change the tech stack** — use what's already there"
        "\n6. **Test after every change** — build, start, verify it still works"
        "\n7. **Update README.md** if you change how to install/run/test"
    ),
    "test": (
        "\n\n## EXISTING PROJECT MODE"
        "\n\nThis is an EXISTING project. When testing:"
        "\n1. Check for existing tests first — run them, see what passes/fails"
        "\n2. Fix failing existing tests before writing new ones"
        "\n3. Write tests that cover the user's requested changes"
        "\n4. Don't break existing test infrastructure (test config, helpers, fixtures)"
    ),
    "verify": (
        "\n\n## EXISTING PROJECT MODE"
        "\n\nThis is an EXISTING project. Focus verification on:"
        "\n1. Does the app start and run after the builder's changes?"
        "\n2. Did the builder break any existing functionality?"
        "\n3. Were the user's requested changes actually implemented?"
        "\n4. Is the README still accurate?"
    ),
    "improve": (
        "\n\n## EXISTING PROJECT MODE"
        "\n\nThis is an EXISTING project. When improving:"
        "\n1. Focus on fixing what the builder changed/broke, not rewriting unrelated code"
        "\n2. Ensure existing functionality still works"
        "\n3. Only refactor code that was touched in this round"
        "\n4. Update README and CLAUDE.md if anything changed"
    ),
}

DEFAULT_EXISTING_INSTRUCTIONS = (
    "\n\n## EXISTING PROJECT MODE"
    "\n\nThis is an EXISTING project with code already in the working directory. "
    "You MUST:"
    "\n1. First explore and understand the existing codebase (read files, check structure)"
    "\n2. Identify the tech stack, frameworks, and patterns already in use"
    "\n3. Work WITH the existing code — do not rewrite from scratch"
    "\n4. Preserve existing functionality while making improvements"
    "\n5. If the existing code doesn't work, fix it before adding anything new"
)


class BasePhase(abc.ABC):
    name: str = ""
    default_timeout: int = 600

    def __init__(self, context: ProjectContext, agent_manager: AgentManager, config: BuilderConfig, error_memory: ErrorMemory | None = None):
        self.context = context
        self.agent_manager = agent_manager
        self.config = config
        self.error_memory = error_memory

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
        # Inject error memory so agents learn from past failures
        if self.error_memory:
            error_context = self.error_memory.get_context_prompt()
            if error_context:
                prompt += f"\n\n{error_context}"
        if self.config.existing_project:
            prompt += EXISTING_PROJECT_INSTRUCTIONS.get(self.name, DEFAULT_EXISTING_INSTRUCTIONS)
        return prompt

    def _should_include_repo_map(self) -> bool:
        """In existing project mode, ALL phases get the repo map for codebase awareness."""
        if self.config.existing_project:
            return True
        return self.name in REPO_MAP_PHASES

    def _build_task_prompt(self, round_number: int) -> str:
        if self.config.existing_project:
            parts = [f"Work on the existing project: {self.config.prompt}"]
        else:
            parts = [f"Build the following: {self.config.prompt}"]
        # Include repo map for codebase awareness
        if self._should_include_repo_map():
            try:
                repo_map = generate_repo_map(self.context.project_dir)
                if repo_map.strip():
                    parts.append(f"\n--- Repository Map ---\n{repo_map}")
            except Exception:
                pass  # Don't fail if repo map generation fails
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
