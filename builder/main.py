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


def run_wizard() -> BuilderConfig:
    print("\n  Builder - Autonomous AI Agent Orchestrator\n")

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

    print(f"\n  Summary:")
    print(f"  Prompt:   {prompt_text}")
    print(f"  Type:     {project_type.value}")
    print(f"  Rounds:   {rounds}")
    print(f"  Note:     Multiple rounds will consume significant tokens.\n")

    confirm = inquirer.confirm(message="Start building?", default=True).execute()

    if not confirm:
        print("Cancelled.")
        sys.exit(0)

    return BuilderConfig(prompt=prompt_text, project_type=project_type, rounds=rounds)


def check_resume(ctx: ProjectContext) -> bool | None:
    if not ctx.has_previous_run():
        return None
    state = ctx.load_state()
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
        config = run_wizard()
        if resume is False:
            ctx.archive_previous_run()
        ctx.initialize(config)

    event_queue = asyncio.Queue()
    orchestrator = Orchestrator(context=ctx, config=config, event_queue=event_queue)
    asyncio.run(run_with_dashboard(orchestrator, config, event_queue))


if __name__ == "__main__":
    main()
