import asyncio
import subprocess
from pathlib import Path

from builder.agents import AgentManager
from builder.context import ProjectContext
from builder.events import (
    LogMessage,
    PhaseCompleted,
    PhaseStarted,
    RoundCompleted,
    RoundStarted,
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
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True

    async def _emit(self, event) -> None:
        await self.event_queue.put(event)

    async def run(self) -> None:
        self._ensure_git_repo()
        state = self.context.load_state()
        start_round = state.current_round

        for round_num in range(start_round, self.config.rounds + 1):
            if self._cancelled:
                break
            await self._emit(RoundStarted(round_number=round_num, total_rounds=self.config.rounds))
            await self._run_round(round_num)
            if self._cancelled:
                break
            await self._emit(RoundCompleted(round_number=round_num))
            self._git_commit_round(round_num)

        self.context.save_token_usage(self.token_breakdown, self.total_tokens)
        cost_usd = self.agent_manager.total_cost_usd
        await self._emit(LogMessage(message=f"Build complete! Total cost: ${cost_usd:.2f}"))

    async def _run_round(self, round_number: int) -> None:
        self.token_breakdown.setdefault(f"round_{round_number}", {})

        state = self.context.load_state()
        phases_to_run = self._get_remaining_phases(state, round_number)

        for phase_name in phases_to_run:
            if self._cancelled:
                break
            phase_class = PHASE_CLASSES[phase_name]
            phase = phase_class(context=self.context, agent_manager=self.agent_manager, config=self.config)
            success = await self._run_phase(phase, round_number)
            status = PhaseStatus.COMPLETED if success else PhaseStatus.FAILED_SKIPPED
            self.context.update_phase_status(round_number, phase_name, status)
            self._git_checkpoint(round_number, phase_name, success)

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

            # Track tokens even on failure
            self.total_tokens += result.token_usage
            self.token_breakdown.setdefault(f"round_{round_number}", {})[phase.name] = result.token_usage
            await self._emit(TokenUpdate(total_tokens=self.total_tokens, phase_tokens=result.token_usage))

            if not result.success:
                # Retry agent failures too (not just validation failures)
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

    def _git_checkpoint(self, round_number: int, phase_name: str, success: bool) -> None:
        """Commit after each phase for mid-round rollback support."""
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
