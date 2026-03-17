import asyncio
import json
import subprocess
from pathlib import Path

from builder.agents import AgentManager
from builder.context import ProjectContext
from builder.error_memory import ErrorMemory
from builder.events import (
    BudgetExceeded,
    LogMessage,
    PhaseCompleted,
    PhaseStarted,
    RoundCompleted,
    RoundStarted,
    SpecApprovalRequested,
    TokenUpdate,
)
from builder.models import (
    AgentResult,
    BuilderConfig,
    PhaseStatus,
    StateData,
    PHASE_NAMES,
)
from builder.phases import PHASE_CLASSES
from builder.phases.base import BasePhase


class Orchestrator:
    MAX_PHASE_RETRIES = 3

    def __init__(self, context: ProjectContext, config: BuilderConfig, event_queue: asyncio.Queue):
        self.context = context
        self.config = config
        self.event_queue = event_queue
        self.agent_manager = AgentManager(event_queue=event_queue)
        self.total_tokens = 0
        self.token_breakdown: dict = {}
        self.error_memory = ErrorMemory(context.builder_dir)
        self._cancelled = False
        self._spec_approved = asyncio.Event()
        if not config.approve_spec:
            self._spec_approved.set()

    def cancel(self) -> None:
        self._cancelled = True
        self._spec_approved.set()

    def approve_spec(self) -> None:
        """Called by the dashboard/UI when user approves the spec."""
        self._spec_approved.set()

    async def _emit(self, event) -> None:
        await self.event_queue.put(event)

    def _check_budget(self) -> bool:
        if self.config.max_cost_usd is None:
            return False
        return self.agent_manager.total_cost_usd >= self.config.max_cost_usd

    async def _send_webhook(self, payload: dict) -> None:
        if not self.config.webhook_url:
            return
        try:
            import urllib.request
            data = json.dumps(payload).encode()
            req = urllib.request.Request(
                self.config.webhook_url,
                data=data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            await asyncio.get_running_loop().run_in_executor(
                None, lambda: urllib.request.urlopen(req, timeout=5)
            )
        except Exception:
            pass

    async def run(self) -> None:
        self._ensure_git_repo()
        state = self.context.load_state()
        start_round = state.current_round

        for round_num in range(start_round, self.config.rounds + 1):
            if self._cancelled:
                break
            await self._emit(RoundStarted(round_number=round_num, total_rounds=self.config.rounds))
            await self._send_webhook({"event": "round_started", "round": round_num, "total": self.config.rounds})
            await self._run_round(round_num)
            if self._cancelled:
                break
            await self._emit(RoundCompleted(round_number=round_num))
            await self._send_webhook({"event": "round_completed", "round": round_num})
            self._git_commit_round(round_num)

        self.context.save_token_usage(self.token_breakdown, self.total_tokens)
        cost_usd = self.agent_manager.total_cost_usd
        await self._emit(LogMessage(message=f"Build complete! Total cost: ${cost_usd:.2f}"))
        await self._send_webhook({"event": "build_complete", "cost_usd": cost_usd})

    async def _run_round(self, round_number: int) -> None:
        self.token_breakdown.setdefault(f"round_{round_number}", {})

        state = self.context.load_state()
        phases_to_run = self._get_remaining_phases(state, round_number)

        for phase_name in phases_to_run:
            if self._cancelled:
                break

            # Budget check before each phase
            if self._check_budget():
                await self._emit(BudgetExceeded(
                    current_cost=self.agent_manager.total_cost_usd,
                    max_cost=self.config.max_cost_usd,
                ))
                await self._emit(LogMessage(
                    message=f"Budget exceeded: ${self.agent_manager.total_cost_usd:.2f} / ${self.config.max_cost_usd:.2f}",
                    level="error",
                ))
                self._cancelled = True
                break

            # Approval gate: pause before research on round 1 so user can review spec
            if phase_name == "research" and round_number == 1 and self.config.approve_spec:
                spec_path = self.context.get_phase_output_path(round_number, "brainstorm")
                if spec_path.exists():
                    await self._emit(SpecApprovalRequested(spec_path=str(spec_path)))
                    await self._emit(LogMessage(
                        message="Waiting for spec approval... (press 'a' in dashboard to approve)",
                        level="info",
                    ))
                    await self._spec_approved.wait()
                    if self._cancelled:
                        break

            phase_class = PHASE_CLASSES[phase_name]
            phase = phase_class(context=self.context, agent_manager=self.agent_manager, config=self.config, error_memory=self.error_memory)

            pre_phase_hash = self._get_git_hash()

            success = await self._run_phase(phase, round_number)
            status = PhaseStatus.COMPLETED if success else PhaseStatus.FAILED_SKIPPED
            self.context.update_phase_status(round_number, phase_name, status)
            self._git_checkpoint(round_number, phase_name, success)

            await self._send_webhook({
                "event": "phase_completed",
                "round": round_number,
                "phase": phase_name,
                "success": success,
                "cost_usd": self.agent_manager.total_cost_usd,
            })

            # Rollback on regression: if test or improve made things worse, revert
            if phase_name in ("test", "improve") and not success and pre_phase_hash:
                await self._emit(LogMessage(
                    message=f"{phase_name} failed — rolling back to pre-phase state",
                    level="warning",
                ))
                self._git_rollback(pre_phase_hash)

        if not self._cancelled:
            state = self.context.load_state()
            state.current_round = round_number + 1
            state.current_phase = "brainstorm"
            state.phase_status = PhaseStatus.PENDING
            state.retry_count = 0
            self.context.save_state(state)

    async def _run_phase(self, phase: BasePhase, round_number: int) -> bool:
        await self._emit(PhaseStarted(round_number=round_number, phase_name=phase.name))
        self.context.update_phase_status(round_number, phase.name, PhaseStatus.IN_PROGRESS)

        for attempt in range(1, self.MAX_PHASE_RETRIES + 1):
            if self._cancelled:
                return False

            result = await phase.run(round_number)

            self.total_tokens += result.token_usage
            self.token_breakdown.setdefault(f"round_{round_number}", {})[phase.name] = result.token_usage
            await self._emit(TokenUpdate(total_tokens=self.total_tokens, phase_tokens=result.token_usage))

            if not result.success:
                if result.error:
                    self.error_memory.record_error(phase.name, round_number, result.error)
                if attempt < self.MAX_PHASE_RETRIES:
                    await self._emit(LogMessage(
                        message=f"{phase.name} agent failed (attempt {attempt}/{self.MAX_PHASE_RETRIES}): {result.error}",
                        level="warning",
                    ))
                    continue
                else:
                    await self._emit(LogMessage(
                        message=f"{phase.name} failed after {self.MAX_PHASE_RETRIES} attempts: {result.error}",
                        level="error",
                    ))
                    await self._emit(PhaseCompleted(round_number=round_number, phase_name=phase.name, success=False))
                    return False

            is_valid, error_msg = phase.validate(round_number)
            if is_valid:
                self.context.update_phase_status(round_number, phase.name, PhaseStatus.COMPLETED)
                await self._emit(PhaseCompleted(round_number=round_number, phase_name=phase.name, success=True))
                return True

            self.error_memory.record_error(phase.name, round_number, f"Validation: {error_msg}")
            if attempt < self.MAX_PHASE_RETRIES:
                await self._emit(LogMessage(
                    message=f"{phase.name} validation failed (attempt {attempt}/{self.MAX_PHASE_RETRIES}): {error_msg}",
                    level="warning",
                ))
            else:
                await self._emit(LogMessage(
                    message=f"{phase.name} validation failed after {self.MAX_PHASE_RETRIES} attempts: {error_msg}",
                    level="error",
                ))

        await self._emit(PhaseCompleted(round_number=round_number, phase_name=phase.name, success=False))
        return False

    def _get_remaining_phases(self, state: StateData, round_number: int) -> list[str]:
        round_key = str(round_number)
        if round_key not in state.rounds:
            return list(PHASE_NAMES)
        round_state = state.rounds[round_key]
        remaining = []
        for phase in PHASE_NAMES:
            status = round_state.phases.get(phase, PhaseStatus.PENDING)
            if status in (PhaseStatus.PENDING, PhaseStatus.IN_PROGRESS, PhaseStatus.FAILED_SKIPPED):
                remaining.append(phase)
        return remaining

    def _ensure_git_repo(self) -> None:
        git_dir = self.context.project_dir / ".git"
        if not git_dir.exists():
            subprocess.run(["git", "init"], cwd=self.context.project_dir, capture_output=True)

    def _get_git_hash(self) -> str | None:
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.context.project_dir,
                capture_output=True,
                text=True,
            )
            return result.stdout.strip() if result.returncode == 0 else None
        except Exception:
            return None

    def _git_rollback(self, commit_hash: str) -> None:
        try:
            subprocess.run(
                ["git", "revert", "--no-commit", "HEAD"],
                cwd=self.context.project_dir,
                capture_output=True,
            )
            subprocess.run(
                ["git", "commit", "-m", "builder: rollback — phase regression detected"],
                cwd=self.context.project_dir,
                capture_output=True,
            )
        except Exception:
            pass

    def _git_checkpoint(self, round_number: int, phase_name: str, success: bool) -> None:
        status = "completed" if success else "failed"
        try:
            subprocess.run(["git", "add", "-A"], cwd=self.context.project_dir, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", f"builder: round {round_number} - {phase_name} {status}"],
                cwd=self.context.project_dir,
                capture_output=True,
            )
        except Exception:
            pass

    def _git_commit_round(self, round_number: int) -> None:
        try:
            subprocess.run(["git", "add", "-A"], cwd=self.context.project_dir, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", f"builder: round {round_number} complete"],
                cwd=self.context.project_dir,
                capture_output=True,
            )
        except Exception:
            pass
