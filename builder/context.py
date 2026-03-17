import json
import shutil
from pathlib import Path

from builder.models import (
    BuilderConfig,
    PhaseStatus,
    RoundState,
    StateData,
    PHASE_NAMES,
)

PHASE_OUTPUT_MAP = {
    "brainstorm": ("specs", "round-{round}-spec.md"),
    "research": ("research", "round-{round}-research.md"),
    "build": ("", ""),
    "verify": ("verification", "round-{round}-verify.md"),
    "test": ("testing", "round-{round}-results.md"),
    "improve": ("improvements", "round-{round}-improvements.md"),
}


class ProjectContext:
    def __init__(self, project_dir: Path):
        self.project_dir = Path(project_dir)
        self.builder_dir = self.project_dir / ".builder"

    def initialize(self, config: BuilderConfig) -> None:
        self.builder_dir.mkdir(exist_ok=True)
        for subdir in ["specs", "research", "verification", "testing", "improvements", "logs"]:
            (self.builder_dir / subdir).mkdir(exist_ok=True)
        config_path = self.builder_dir / "config.json"
        config_path.write_text(config.model_dump_json(indent=2))
        initial_state = StateData(
            current_round=1,
            total_rounds=config.rounds,
            current_phase="brainstorm",
            phase_status=PhaseStatus.PENDING,
            retry_count=0,
            rounds={},
        )
        self.save_state(initial_state)

    def has_previous_run(self) -> bool:
        return (self.builder_dir / "state.json").exists()

    def archive_previous_run(self) -> None:
        bak_dir = self.project_dir / ".builder.bak"
        if bak_dir.exists():
            shutil.rmtree(bak_dir)
        shutil.move(str(self.builder_dir), str(bak_dir))

    def load_config(self) -> BuilderConfig:
        config_path = self.builder_dir / "config.json"
        return BuilderConfig.model_validate_json(config_path.read_text())

    def load_state(self) -> StateData:
        state_path = self.builder_dir / "state.json"
        return StateData.model_validate_json(state_path.read_text())

    def save_state(self, state: StateData) -> None:
        state_path = self.builder_dir / "state.json"
        state_path.write_text(state.model_dump_json(indent=2))

    def update_phase_status(self, round_number: int, phase_name: str, status: PhaseStatus) -> None:
        state = self.load_state()
        round_key = str(round_number)
        if round_key not in state.rounds:
            state.rounds[round_key] = RoundState(
                phases={p: PhaseStatus.PENDING for p in PHASE_NAMES}
            )
        state.rounds[round_key].phases[phase_name] = status
        state.current_phase = phase_name
        state.phase_status = status
        self.save_state(state)

    def get_phase_output_path(self, round_number: int, phase_name: str) -> Path:
        subdir, pattern = PHASE_OUTPUT_MAP[phase_name]
        if not subdir:
            return self.project_dir
        filename = pattern.format(round=round_number)
        return self.builder_dir / subdir / filename

    # Context priority: which prior phases matter most to each current phase
    CONTEXT_PRIORITY = {
        "brainstorm": [],
        "research": ["brainstorm"],
        "build": ["brainstorm", "research"],
        "verify": ["brainstorm"],
        "test": ["brainstorm", "verify"],
        "improve": ["brainstorm", "verify", "test"],
    }

    def get_context_files(self, round_number: int, phase_name: str) -> list[str]:
        files = []
        config_path = self.builder_dir / "config.json"
        if config_path.exists():
            files.append(str(config_path))
        # Include project CLAUDE.md for verify/test/improve
        claude_md = self.project_dir / "CLAUDE.md"
        if claude_md.exists() and phase_name in ("verify", "test", "improve"):
            files.append(str(claude_md))
        # Priority-based context: only include what's relevant
        priority_phases = self.CONTEXT_PRIORITY.get(phase_name, [])
        for prior_phase in priority_phases:
            output_path = self.get_phase_output_path(round_number, prior_phase)
            if output_path.exists() and output_path.is_file():
                files.append(str(output_path))
        if round_number > 1:
            prev_improve = self.get_phase_output_path(round_number - 1, "improve")
            if prev_improve.exists() and prev_improve.is_file():
                files.append(str(prev_improve))
        return files

    def save_token_usage(self, breakdown: dict, total: int) -> None:
        usage_path = self.builder_dir / "logs" / "token-usage.json"
        data = {"breakdown": breakdown, "total": total}
        usage_path.write_text(json.dumps(data, indent=2))
