import asyncio
import sys
from pathlib import Path

from InquirerPy import inquirer

from builder.context import ProjectContext
from builder.dashboard.app import BuilderDashboard
from builder.events import ShutdownRequested
from builder.models import BuilderConfig, ProjectType
from builder.orchestrator import Orchestrator


PROJECT_TYPE_CHOICES = [
    {"name": "Web App", "value": ProjectType.WEB_APP},
    {"name": "CLI Tool", "value": ProjectType.CLI_TOOL},
    {"name": "API / Backend", "value": ProjectType.API_BACKEND},
    {"name": "Library / Package", "value": ProjectType.LIBRARY},
    {"name": "Mobile App", "value": ProjectType.MOBILE_APP},
    {"name": "Other", "value": ProjectType.OTHER},
]

SOURCE_EXTENSIONS = {
    ".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css",
    ".go", ".rs", ".java", ".rb", ".php", ".swift", ".kt",
}

SKIP_DIRS = {"node_modules", "__pycache__", ".git", "venv", ".venv", ".builder", ".builder.bak"}


def _has_existing_code(project_dir: Path) -> bool:
    """Check if the directory contains source code files."""
    for entry in project_dir.iterdir():
        if entry.name.startswith(".") or entry.name in SKIP_DIRS:
            continue
        if entry.is_file() and entry.suffix in SOURCE_EXTENSIONS:
            return True
        if entry.is_dir() and entry.name not in SKIP_DIRS:
            for sub in entry.rglob("*"):
                if sub.is_file() and sub.suffix in SOURCE_EXTENSIONS:
                    return True
    return False


def run_wizard(existing_code: bool = False) -> BuilderConfig:
    print("\n  Builder - Autonomous AI Agent Orchestrator\n")

    is_existing = False

    if existing_code:
        mode = inquirer.select(
            message="Existing project detected. What would you like to do?",
            choices=[
                {"name": "Fix & improve — verify it works, fix bugs, improve quality", "value": "fix"},
                {"name": "Add features — describe what to add to the existing project", "value": "add"},
                {"name": "Start fresh — ignore existing code, build from scratch", "value": "fresh"},
            ],
        ).execute()

        if mode == "fresh":
            is_existing = False
            prompt_text = inquirer.text(
                message="What would you like to build?",
                validate=lambda x: len(x.strip()) > 0,
                invalid_message="Please describe what you want to build.",
            ).execute()
        elif mode == "fix":
            is_existing = True
            prompt_text = inquirer.text(
                message="Describe what the project should do (or press Enter to auto-analyze):",
                default="",
            ).execute()
            if not prompt_text.strip():
                prompt_text = (
                    "Analyze the existing project, verify it works correctly, fix any bugs or issues, "
                    "improve code quality, update dependencies to latest versions, and ensure it has "
                    "a complete README with setup and run instructions."
                )
        else:  # add
            is_existing = True
            prompt_text = inquirer.text(
                message="What features would you like to add?",
                validate=lambda x: len(x.strip()) > 0,
                invalid_message="Please describe the features to add.",
            ).execute()
    else:
        prompt_text = inquirer.text(
            message="What would you like to build?",
            validate=lambda x: len(x.strip()) > 0,
            invalid_message="Please describe what you want to build.",
        ).execute()

    project_type = inquirer.select(
        message="What type of project?",
        choices=PROJECT_TYPE_CHOICES,
    ).execute()

    rounds = inquirer.number(
        message="How many iteration rounds? (1-10)",
        default=3,
        min_allowed=1,
        max_allowed=10,
    ).execute()

    rounds = int(rounds)

    mode_label = "Existing project" if is_existing else "New project"
    print(f"\n  Summary:")
    print(f"  Mode:     {mode_label}")
    print(f"  Prompt:   {prompt_text[:80]}{'...' if len(prompt_text) > 80 else ''}")
    print(f"  Type:     {project_type.value}")
    print(f"  Rounds:   {rounds}")
    print(f"  Note:     Multiple rounds will consume significant tokens.")

    # Supabase MCP reminder for projects that likely need it
    needs_supabase = project_type in (ProjectType.WEB_APP, ProjectType.MOBILE_APP, ProjectType.API_BACKEND)
    if needs_supabase:
        print(f"\n  Supabase: This project type may use Supabase for backend/auth/database.")
        print(f"            For best results, configure the Supabase MCP server in Claude Code:")
        print(f"            https://github.com/supabase-community/supabase-mcp")
        print(f"            This lets builder agents create tables, set up auth, and test")
        print(f"            against your real Supabase project automatically.")
    print()

    confirm = inquirer.confirm(message="Start building?", default=True).execute()

    if not confirm:
        print("Cancelled.")
        sys.exit(0)

    return BuilderConfig(
        prompt=prompt_text,
        project_type=project_type,
        rounds=rounds,
        existing_project=is_existing,
    )


def check_resume(ctx: ProjectContext) -> bool | None:
    if not ctx.has_previous_run():
        return None
    state = ctx.load_state()
    if state.current_round > state.total_rounds:
        print(f"\n  Previous build completed ({state.total_rounds} rounds).")
        return inquirer.confirm(message="Start fresh?", default=True).execute() and False
    print(
        f"\n  Previous build detected "
        f"(Round {state.current_round}/{state.total_rounds}, "
        f"Phase: {state.current_phase})"
    )
    return inquirer.confirm(message="Resume previous build?", default=True).execute()


async def run_with_dashboard(orchestrator: Orchestrator, config: BuilderConfig, event_queue: asyncio.Queue) -> None:
    dashboard = BuilderDashboard(
        event_queue=event_queue,
        project_name=config.prompt[:50],
        total_rounds=config.rounds,
        existing_project=config.existing_project,
        orchestrator=orchestrator,
    )

    original_exit = dashboard.exit

    def patched_exit(*args, **kwargs):
        orchestrator.cancel()
        original_exit(*args, **kwargs)

    dashboard.exit = patched_exit

    async def orchestrator_task():
        try:
            await orchestrator.run()
        except Exception as e:
            await event_queue.put(ShutdownRequested())
        finally:
            await asyncio.sleep(2)
            await event_queue.put(ShutdownRequested())

    task = asyncio.create_task(orchestrator_task())
    await dashboard.run_async()

    if not task.done():
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


def main():
    project_dir = Path.cwd()
    ctx = ProjectContext(project_dir=project_dir)

    resume = check_resume(ctx)

    if resume is True:
        config = ctx.load_config()
    else:
        existing_code = _has_existing_code(project_dir)
        config = run_wizard(existing_code=existing_code)
        if resume is False:
            ctx.archive_previous_run()
        ctx.initialize(config)

    event_queue = asyncio.Queue()
    orchestrator = Orchestrator(context=ctx, config=config, event_queue=event_queue)
    asyncio.run(run_with_dashboard(orchestrator, config, event_queue))


if __name__ == "__main__":
    main()
