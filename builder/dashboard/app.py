import asyncio
from datetime import datetime

from textual.app import App, ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Header, Footer, Static, RichLog
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
    CostUpdate,
    SpecApprovalRequested,
    BudgetExceeded,
    ShutdownRequested,
)
from builder.models import PHASE_NAMES, EXISTING_PHASE_NAMES


# ── Phase display config ────────────────────────────────────────────

PHASE_ICONS = {
    "pending": "[dim]\u25cb[/dim]",            # ○
    "in_progress": "[yellow]\u25cf[/yellow]",  # ●
    "completed": "[green]\u2713[/green]",      # ✓
    "failed_skipped": "[red]\u2717[/red]",     # ✗
}

PHASE_MODELS = {
    "brainstorm": "opus",
    "research": "opus \u00d73",
    "design": "opus",
    "setup": "sonnet",
    "build": "sonnet",
    "test": "sonnet",
    "verify": "opus \u00d73",
    "improve": "opus",
}


# ── Custom Widgets ──────────────────────────────────────────────────

class PhaseTracker(Static):
    """Shows all phases with status icons, model labels, and elapsed time."""

    phase_statuses: reactive[dict[str, str]] = reactive(
        lambda: {p: "pending" for p in PHASE_NAMES}
    )
    phase_times: reactive[dict[str, str]] = reactive(dict)
    active_phase: reactive[str] = reactive("")
    phase_list: reactive[list[str]] = reactive(lambda: list(PHASE_NAMES))

    def render(self) -> str:
        lines = [" [bold]PHASES[/bold]", ""]
        for phase in self.phase_list:
            status = self.phase_statuses.get(phase, "pending")
            icon = PHASE_ICONS.get(status, PHASE_ICONS["pending"])
            label = phase.capitalize()
            model = PHASE_MODELS.get(phase, "")
            time_str = self.phase_times.get(phase, "")

            line = f"  {icon} {label}"
            if model:
                line += f" [dim]{model}[/dim]"
            if time_str:
                line += f" [dim]{time_str}[/dim]"
            if phase == self.active_phase and status == "in_progress":
                line += " [yellow]\u2026[/yellow]"
            lines.append(line)
        return "\n".join(lines)


class ActiveAgents(Static):
    """Shows currently running agents."""

    agents: reactive[dict[str, str]] = reactive(dict)

    def render(self) -> str:
        lines = [" [bold]AGENTS[/bold]", ""]
        if not self.agents:
            lines.append("  [dim]Waiting...[/dim]")
        else:
            for agent_id, desc in self.agents.items():
                short = desc[:20] + "\u2026" if len(desc) > 20 else desc
                lines.append(f"  [cyan]\u25b8[/cyan] [dim]{agent_id}[/dim] {short}")
        return "\n".join(lines)


class PhaseProgress(Static):
    """Visual progress bar for phase completion."""

    completed: reactive[int] = reactive(0)
    total: reactive[int] = reactive(8)

    def render(self) -> str:
        pct = self.completed / max(self.total, 1)
        filled = int(pct * 16)
        empty = 16 - filled
        bar = f"[green]{'\u2588' * filled}[/green][dim]{'\u2591' * empty}[/dim]"
        lines = [
            " [bold]PROGRESS[/bold]",
            "",
            f"  {bar}",
            f"  [bold]{self.completed}[/bold][dim]/{self.total} phases[/dim]",
        ]
        return "\n".join(lines)


class ApprovalBanner(Static):
    """Shows when spec approval is needed."""

    visible: reactive[bool] = reactive(False)

    def render(self) -> str:
        if not self.visible:
            return ""
        return (
            "[bold on yellow] SPEC READY [/bold on yellow] "
            "Review the spec, then press [bold]a[/bold] to approve"
        )


class StatusLine(Static):
    """Bottom status bar with cost, time, round, and phase info."""

    cost: reactive[float] = reactive(0.0)
    elapsed: reactive[str] = reactive("0:00:00")
    round_info: reactive[str] = reactive("1/1")
    phase_info: reactive[str] = reactive("0/8")

    def render(self) -> str:
        cost_str = f"${self.cost:.2f}"
        parts = [
            f"[bold]{cost_str}[/bold]",
            self.elapsed,
            f"Round {self.round_info}",
            f"{self.phase_info} phases",
            "[dim]q[/dim]:quit  [dim]a[/dim]:approve",
        ]
        return " \u2502 ".join(parts)


# ── Main App ────────────────────────────────────────────────────────

class BuilderDashboard(App):
    CSS = """
    Screen {
        background: $surface;
    }
    #main {
        layout: horizontal;
        height: 1fr;
    }
    #sidebar {
        width: 34;
        padding: 1 0;
        border-right: tall $primary-background-lighten-2;
    }
    #log-panel {
        width: 1fr;
        padding: 0 1;
    }
    #log-title {
        height: 3;
        padding: 1 1 0 1;
    }
    #log {
        height: 1fr;
        scrollbar-size: 1 1;
    }
    #status-line {
        dock: bottom;
        height: 1;
        padding: 0 1;
        background: $primary-background;
        color: $text;
    }
    #approval-banner {
        dock: bottom;
        height: auto;
        padding: 0 1;
    }
    PhaseTracker {
        height: auto;
        margin-bottom: 1;
    }
    ActiveAgents {
        height: auto;
        margin-bottom: 1;
    }
    PhaseProgress {
        height: auto;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("a", "approve_spec", "Approve spec"),
    ]

    def __init__(
        self,
        event_queue: asyncio.Queue,
        project_name: str = "Builder",
        total_rounds: int = 1,
        existing_project: bool = False,
        orchestrator=None,
    ):
        super().__init__()
        self.event_queue = event_queue
        self.project_name = project_name
        self.total_rounds = total_rounds
        self.existing_project = existing_project
        self.orchestrator = orchestrator
        self.current_round = 1
        self._active_agents: dict[str, str] = {}
        self._elapsed_start = datetime.now()
        self._phase_start_times: dict[str, datetime] = {}
        self._completed_phases = 0
        self._phase_list = list(EXISTING_PHASE_NAMES if existing_project else PHASE_NAMES)

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main"):
            with Vertical(id="sidebar"):
                yield PhaseTracker()
                yield ActiveAgents()
                yield PhaseProgress()
            with Vertical(id="log-panel"):
                yield Static(
                    f" [bold]{self.project_name}[/bold] "
                    f"[dim]\u2014 Round 1/{self.total_rounds}[/dim]",
                    id="log-title",
                )
                yield RichLog(highlight=True, markup=True, id="log")
        yield ApprovalBanner(id="approval-banner")
        yield StatusLine(id="status-line")

    def on_mount(self) -> None:
        self.title = "Builder"
        self.sub_title = self.project_name

        tracker = self.query_one(PhaseTracker)
        tracker.phase_list = self._phase_list
        tracker.phase_statuses = {p: "pending" for p in self._phase_list}

        progress = self.query_one(PhaseProgress)
        progress.total = len(self._phase_list)

        status = self.query_one("#status-line", StatusLine)
        status.round_info = f"1/{self.total_rounds}"
        status.phase_info = f"0/{len(self._phase_list)}"

        self.set_interval(1.0, self._update_elapsed)
        asyncio.get_running_loop().create_task(self._consume_events())

    def action_approve_spec(self) -> None:
        if self.orchestrator:
            self.orchestrator.approve_spec()
        banner = self.query_one("#approval-banner", ApprovalBanner)
        banner.visible = False
        log = self.query_one("#log", RichLog)
        log.write("[green]Spec approved \u2713[/green]")

    def _update_elapsed(self) -> None:
        delta = datetime.now() - self._elapsed_start
        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        self.query_one("#status-line", StatusLine).elapsed = (
            f"{hours}:{minutes:02d}:{seconds:02d}"
        )

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
            self._completed_phases = 0

            self.query_one("#log-title", Static).update(
                f" [bold]{self.project_name}[/bold] "
                f"[dim]\u2014 Round {event.round_number}/{event.total_rounds}[/dim]"
            )
            self.query_one("#status-line", StatusLine).round_info = (
                f"{event.round_number}/{event.total_rounds}"
            )

            tracker = self.query_one(PhaseTracker)
            tracker.phase_statuses = {p: "pending" for p in self._phase_list}
            tracker.phase_times = {}
            tracker.active_phase = ""

            self.query_one(PhaseProgress).completed = 0

            log.write("")
            log.write(
                f"[bold]\u2500\u2500\u2500 Round "
                f"{event.round_number}/{event.total_rounds} "
                f"\u2500\u2500\u2500[/bold]"
            )
            log.write("")

        elif isinstance(event, RoundCompleted):
            log.write("")
            log.write(
                f"[bold green]\u2713 Round {event.round_number} complete[/bold green]"
            )
            log.write("")

        elif isinstance(event, PhaseStarted):
            tracker = self.query_one(PhaseTracker)
            statuses = dict(tracker.phase_statuses)
            statuses[event.phase_name] = "in_progress"
            tracker.phase_statuses = statuses
            tracker.active_phase = event.phase_name
            self._phase_start_times[event.phase_name] = datetime.now()

            model = PHASE_MODELS.get(event.phase_name, "")
            log.write(
                f"[bold]{ts}[/bold] [yellow]\u25cf[/yellow] "
                f"[bold]{event.phase_name}[/bold] started"
                f" [dim]({model})[/dim]"
            )

        elif isinstance(event, PhaseCompleted):
            tracker = self.query_one(PhaseTracker)
            statuses = dict(tracker.phase_statuses)
            statuses[event.phase_name] = (
                "completed" if event.success else "failed_skipped"
            )
            tracker.phase_statuses = statuses
            tracker.active_phase = ""

            # Calculate elapsed time for this phase
            times = dict(tracker.phase_times)
            start = self._phase_start_times.get(event.phase_name)
            if start:
                delta = (datetime.now() - start).total_seconds()
                if delta >= 60:
                    mins = int(delta // 60)
                    secs = int(delta % 60)
                    times[event.phase_name] = f"{mins}m{secs}s"
                else:
                    times[event.phase_name] = f"{int(delta)}s"
            tracker.phase_times = times

            if event.success:
                self._completed_phases += 1
                self.query_one(PhaseProgress).completed = self._completed_phases
                self.query_one("#status-line", StatusLine).phase_info = (
                    f"{self._completed_phases}/{len(self._phase_list)}"
                )
                log.write(
                    f"[bold]{ts}[/bold] [green]\u2713[/green] "
                    f"[bold]{event.phase_name}[/bold] [green]complete[/green]"
                )
            else:
                log.write(
                    f"[bold]{ts}[/bold] [red]\u2717[/red] "
                    f"[bold]{event.phase_name}[/bold] [red]failed[/red]"
                )

        elif isinstance(event, AgentSpawned):
            self._active_agents[event.agent_id] = event.description
            self.query_one(ActiveAgents).agents = dict(self._active_agents)
            log.write(
                f"{ts}   [cyan]\u25b8[/cyan] Spawned agent "
                f"[dim][{event.agent_id}][/dim]"
            )

        elif isinstance(event, AgentOutput):
            text = event.text[:120].replace("\n", " ")
            log.write(f"{ts}   [dim][{event.agent_id}][/dim] {text}")

        elif isinstance(event, AgentFinished):
            self._active_agents.pop(event.agent_id, None)
            self.query_one(ActiveAgents).agents = dict(self._active_agents)

        elif isinstance(event, RetryAttempt):
            reason = (event.reason or event.error)[:80]
            log.write(
                f"[yellow]{ts}   \u21bb Retry "
                f"{event.attempt}/{event.max_retries} "
                f"{event.phase_name}: {reason}[/yellow]"
            )

        elif isinstance(event, LogMessage):
            if event.level == "error":
                log.write(f"[bold red]{ts} \u2718 {event.message}[/bold red]")
            elif event.level == "warning":
                log.write(f"[yellow]{ts} \u26a0 {event.message}[/yellow]")
            else:
                log.write(f"{ts}   {event.message}")

        elif isinstance(event, TokenUpdate):
            pass  # Cost display is more useful

        elif isinstance(event, CostUpdate):
            self.query_one("#status-line", StatusLine).cost = event.total_cost_usd

        elif isinstance(event, SpecApprovalRequested):
            banner = self.query_one("#approval-banner", ApprovalBanner)
            banner.visible = True
            log.write("")
            log.write(
                "[bold on yellow] SPEC READY [/bold on yellow] "
                "Review the brainstorm output, then press "
                "[bold]a[/bold] to approve"
            )
            log.write(f"   Spec file: {event.spec_path}")
            log.write("")

        elif isinstance(event, BudgetExceeded):
            log.write("")
            log.write(
                f"[bold on red] BUDGET EXCEEDED [/bold on red] "
                f"${event.current_cost:.2f} / ${event.max_cost:.2f}"
            )
            log.write("")

        elif isinstance(event, ShutdownRequested):
            log.write("")
            log.write(f"[bold]{ts} Build complete.[/bold]")
            self.exit()
