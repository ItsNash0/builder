import asyncio
from datetime import datetime

from textual.app import App, ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Header, Footer, Static, RichLog, Label
from textual.reactive import reactive

from builder.events import (
    Event,
    PhaseStarted,
    PhaseCompleted,
    AgentSpawned,
    AgentOutput,
    AgentFinished,
    RoundStarted,
    RoundCompleted,
    RetryAttempt,
    LogMessage,
    TokenUpdate,
    ShutdownRequested,
)
from builder.models import PHASE_NAMES


PHASE_ICONS = {
    "pending": "[dim]\u25cb[/dim]",
    "in_progress": "[yellow]\u25c8[/yellow]",
    "completed": "[green]\u2713[/green]",
    "failed_skipped": "[red]\u2717[/red]",
}


class PhaseTracker(Static):
    phase_statuses: reactive[dict[str, str]] = reactive(lambda: {p: "pending" for p in PHASE_NAMES})

    def render(self) -> str:
        lines = ["[bold]Phases[/bold]", ""]
        for phase in PHASE_NAMES:
            status = self.phase_statuses.get(phase, "pending")
            icon = PHASE_ICONS.get(status, PHASE_ICONS["pending"])
            label = phase.capitalize()
            lines.append(f"  {icon} {label}")
        return "\n".join(lines)


class ActiveAgents(Static):
    agents: reactive[dict[str, str]] = reactive(dict)

    def render(self) -> str:
        lines = ["[bold]Active Agents[/bold]", ""]
        if not self.agents:
            lines.append("  [dim]No active agents[/dim]")
        else:
            for agent_id, desc in self.agents.items():
                lines.append(f"  [cyan][{agent_id}][/cyan] {desc}")
        return "\n".join(lines)


class StatusBar(Static):
    total_tokens: reactive[int] = reactive(0)
    elapsed: reactive[str] = reactive("0:00:00")

    def render(self) -> str:
        return f"Tokens: {self.total_tokens:,} | Elapsed: {self.elapsed} | Ctrl+C to cancel"


class BuilderDashboard(App):
    CSS = """
    #main { layout: horizontal; height: 1fr; }
    #sidebar { width: 30; padding: 1; }
    #log-panel { width: 1fr; padding: 1; }
    #status-bar { dock: bottom; height: 1; padding: 0 1; background: $accent; color: $text; }
    PhaseTracker { height: auto; margin-bottom: 1; }
    ActiveAgents { height: auto; }
    """

    BINDINGS = [("q", "quit", "Quit")]

    def __init__(self, event_queue: asyncio.Queue, project_name: str = "Builder", total_rounds: int = 1):
        super().__init__()
        self.event_queue = event_queue
        self.project_name = project_name
        self.total_rounds = total_rounds
        self.current_round = 1
        self._active_agents: dict[str, str] = {}
        self._elapsed_start = datetime.now()

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main"):
            with Vertical(id="sidebar"):
                yield PhaseTracker()
                yield ActiveAgents()
            with Vertical(id="log-panel"):
                yield Label(f"[bold]{self.project_name}[/bold] — Round 1/{self.total_rounds}")
                yield RichLog(highlight=True, markup=True, id="log")
        yield StatusBar(id="status-bar")

    def on_mount(self) -> None:
        self.title = f"Builder - {self.project_name}"
        self.set_interval(1.0, self._update_elapsed)
        asyncio.get_running_loop().create_task(self._consume_events())

    def _update_elapsed(self) -> None:
        delta = datetime.now() - self._elapsed_start
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        self.query_one("#status-bar", StatusBar).elapsed = f"{hours}:{minutes:02d}:{seconds:02d}"

    async def _consume_events(self) -> None:
        while True:
            try:
                event = await asyncio.wait_for(self.event_queue.get(), timeout=0.1)
                self._handle_event(event)
            except asyncio.TimeoutError:
                continue
            except Exception:
                break

    def _handle_event(self, event: Event) -> None:
        log = self.query_one("#log", RichLog)
        ts = event.timestamp.strftime("%H:%M:%S")

        if isinstance(event, RoundStarted):
            self.current_round = event.round_number
            self.query_one(Label).update(
                f"[bold]{self.project_name}[/bold] — Round {event.round_number}/{event.total_rounds}"
            )
            log.write(f"[bold]{ts}[/bold] Round {event.round_number}/{event.total_rounds} started")
            tracker = self.query_one(PhaseTracker)
            tracker.phase_statuses = {p: "pending" for p in PHASE_NAMES}

        elif isinstance(event, RoundCompleted):
            log.write(f"[bold green]{ts}[/bold green] Round {event.round_number} complete")

        elif isinstance(event, PhaseStarted):
            tracker = self.query_one(PhaseTracker)
            statuses = dict(tracker.phase_statuses)
            statuses[event.phase_name] = "in_progress"
            tracker.phase_statuses = statuses
            log.write(f"[bold]{ts}[/bold] Phase: [cyan]{event.phase_name}[/cyan] started")

        elif isinstance(event, PhaseCompleted):
            tracker = self.query_one(PhaseTracker)
            statuses = dict(tracker.phase_statuses)
            statuses[event.phase_name] = "completed" if event.success else "failed_skipped"
            tracker.phase_statuses = statuses
            status_text = "[green]complete[/green]" if event.success else "[red]failed[/red]"
            log.write(f"[bold]{ts}[/bold] Phase: [cyan]{event.phase_name}[/cyan] {status_text}")

        elif isinstance(event, AgentSpawned):
            self._active_agents[event.agent_id] = event.description
            agents_widget = self.query_one(ActiveAgents)
            agents_widget.agents = dict(self._active_agents)
            log.write(f"{ts} Spawned agent [{event.agent_id}]")

        elif isinstance(event, AgentOutput):
            log.write(f"{ts} [{event.agent_id}] {event.text[:100]}")

        elif isinstance(event, AgentFinished):
            self._active_agents.pop(event.agent_id, None)
            agents_widget = self.query_one(ActiveAgents)
            agents_widget.agents = dict(self._active_agents)

        elif isinstance(event, RetryAttempt):
            log.write(
                f"[yellow]{ts}[/yellow] Retry {event.attempt}/{event.max_retries} "
                f"for {event.phase_name}: {event.error[:80]}"
            )

        elif isinstance(event, LogMessage):
            color = {"error": "red", "warning": "yellow"}.get(event.level, "")
            if color:
                log.write(f"[{color}]{ts} {event.message}[/{color}]")
            else:
                log.write(f"{ts} {event.message}")

        elif isinstance(event, TokenUpdate):
            self.query_one("#status-bar", StatusBar).total_tokens = event.total_tokens

        elif isinstance(event, ShutdownRequested):
            log.write(f"[bold red]{ts} Shutting down...[/bold red]")
            self.exit()
