# Builder: Autonomous AI Agent Orchestrator

## Overview

Builder is a Python CLI tool that autonomously builds complete software projects from a simple text prompt. It orchestrates Claude Code subagents through a multi-phase pipeline, iterating over multiple rounds to brainstorm, research, build, verify, test, and improve the output. The user provides a prompt, selects a project type, chooses how many iteration rounds to run, and then waits for the finished product.

## User Interaction

### Startup Wizard

Interactive CLI wizard using `inquirerpy`:

1. **Prompt** — "What would you like to build?" (free text)
2. **Project type** — select from: Web App, CLI Tool, API/Backend, Library/Package, Mobile App, Other
3. **Iteration rounds** — number input (1-10, default 3)
4. **Confirmation** — summary of choices, then execution begins

No further interaction is required until the final output is delivered. The user can press Ctrl+C at any time to gracefully cancel execution. The orchestrator will finish the current agent operation, save state, and exit cleanly.

### Cancellation

- **Ctrl+C** triggers graceful shutdown: the orchestrator signals running agents to stop, waits briefly for cleanup, saves `state.json`, and exits.
- **Double Ctrl+C** forces immediate exit.
- The TUI dashboard displays a "Cancelling..." indicator during graceful shutdown.

### Resume

When `builder` is run in a directory with an existing `.builder/state.json`:

- The wizard detects the previous run and asks: "Previous build detected (Round 2/3, Phase: Build). Resume? (Y/n)"
- If yes: resumes from the last incomplete phase. Phases marked `failed_skipped` are retried on resume (the user may have fixed the environment).
- If no: archives the old `.builder/` to `.builder.bak/` and starts fresh.

### Entry Point

`python -m builder` or installed as `builder` via pyproject.toml `[project.scripts]`.

## Architecture

### Pipeline Orchestrator

A central `Orchestrator` class drives a fixed pipeline of phases. Each phase spawns one or more Claude Code subagents via the SDK with specialized system prompts. Phases are sequential within a round, but agents within a phase can run in parallel.

```
CLI Wizard → Orchestrator → Phase Pipeline → Claude Code SDK → Subagents
```

### Round Loop

Each round executes all 6 phases in sequence. The user selects the total number of rounds at startup. Round 2+ builds on the output of the previous round.

## Phase Pipeline

### Phase 1 — Brainstorm

- Single agent takes the user's prompt + project type and produces a structured product spec.
- Output: `.builder/specs/round-N-spec.md` — features, architecture decisions, tech stack, file structure.
- Round 2+: reviews previous output and improvement suggestions to refine the spec.

### Phase 2 — Research

- Spawns multiple parallel agents (library research, similar projects, API docs).
- Uses web search and documentation tools.
- Output: `.builder/research/round-N-research.md` — findings, recommended libraries, patterns, gotchas.

### Phase 3 — Build

- Main builder agent(s) that write actual code.
- Gets the spec + research as context.
- Round 1: builds from scratch. Round 2+: modifies existing codebase based on updated spec and improvement suggestions.
- Can spawn sub-agents for parallel work (e.g., frontend + backend) if the spec warrants it.
- Output: actual project files in the current directory.

### Phase 4 — Verify

- Agent reviews all generated code for correctness, security issues, missing pieces.
- Checks that code matches the spec.
- Output: `.builder/verification/round-N-verify.md` — issues found, severity ratings.

### Phase 5 — Test

- Agent writes and runs tests (unit, integration as appropriate).
- Executes the test suite and captures results.
- Output: test files + `.builder/testing/round-N-results.md`.

### Phase 6 — Improve

- Analyzes verification results, test results, and overall code quality.
- Produces a prioritized list of improvements for the next round.
- On the final round: spawns a build sub-agent to apply the top-priority improvements directly to the codebase, then re-runs verification and tests.
- Output: `.builder/improvements/round-N-improvements.md`.

## State Management

### `.builder/` Directory

```
.builder/
├── config.json              # User inputs from wizard
├── state.json               # Execution progress
├── specs/
│   └── round-N-spec.md
├── research/
│   └── round-N-research.md
├── verification/
│   └── round-N-verify.md
├── testing/
│   └── round-N-results.md
├── improvements/
│   └── round-N-improvements.md
└── logs/
    └── round-N-phase-name.log
```

### `state.json`

Tracks execution progress with per-round completion history:

```json
{
  "current_round": 2,
  "total_rounds": 3,
  "current_phase": "build",
  "phase_status": "in_progress",
  "retry_count": 0,
  "rounds": {
    "1": {
      "phases": {
        "brainstorm": "completed",
        "research": "completed",
        "build": "completed",
        "verify": "completed",
        "test": "completed",
        "improve": "completed"
      }
    },
    "2": {
      "phases": {
        "brainstorm": "completed",
        "research": "failed_skipped",
        "build": "in_progress",
        "verify": "pending",
        "test": "pending",
        "improve": "pending"
      }
    }
  }
}
```

### Context Flow

- Each agent receives: the user's original prompt, the current round's spec, and outputs from prior phases in the current round.
- Round 2+: agents also receive the previous round's improvement suggestions.
- The orchestrator assembles each agent's prompt from relevant `.builder/` files.

## Claude Code SDK Layer

`AgentManager` is an internal abstraction that wraps the `claude_agent_sdk` Python package. The SDK provides subprocess-based spawning of Claude Code instances. `AgentManager` adds retry logic, parallel dispatch, and result normalization on top of the raw SDK.

### SDK Integration

The `claude_agent_sdk` provides the low-level interface for creating Claude Code subprocesses. `AgentManager` wraps this to provide:

- Consistent error handling and result types
- Parallel agent dispatch with `asyncio.gather`
- Retry logic with error context injection

```python
class AgentManager:
    async def spawn_agent(self, config: AgentConfig) -> AgentResult:
        """Spawn a single Claude Code subagent via claude_agent_sdk.
        Constructs the prompt from config, starts the subprocess,
        streams output to the dashboard, and returns the result."""

    async def spawn_parallel(self, configs: list[AgentConfig]) -> list[AgentResult]:
        """Spawn multiple agents concurrently via asyncio.gather."""

    async def run_with_retry(self, config: AgentConfig, max_retries: int = 3) -> AgentResult:
        """Run an agent with self-healing retry. On failure, appends
        error context to the prompt and retries."""
```

### AgentConfig

- `system_prompt` — role and instructions for the phase
- `context_files` — list of `.builder/` files to include as context in the prompt
- `working_directory` — where the agent operates
- `timeout` — max execution time per agent (default: 10 minutes, Build phase default: 30 minutes)

Note: Claude Code subagents have access to all standard Claude Code tools (file I/O, bash, etc.) by default. Tool access is managed by the Claude Code environment, not by this orchestrator.

### AgentResult

- `success: bool`
- `output: str` — agent's final response
- `files_created: list[str]` — files written by the agent
- `error: str | None` — error details if failed
- `token_usage: int` — tokens consumed by this agent run

## Phase Validation

Each phase defines a `validate()` method on the `BasePhase` class that checks minimum acceptance criteria for the phase output. Validation failure triggers a retry.

| Phase | Validation Criteria |
|-------|-------------------|
| Brainstorm | Output file exists and contains: features list, tech stack, file structure |
| Research | Output file exists and contains at least one library recommendation |
| Build | At least one source file was created/modified in the project directory |
| Verify | Output file exists with a findings section |
| Test | At least one test file exists and test runner executed (pass or fail) |
| Improve | Output file exists with a prioritized improvements list |

## Self-Healing & Error Recovery

1. Agent runs and fails (hard error/crash, or `validate()` returns false).
2. Orchestrator captures the error or validation failure details.
3. Respawns agent with original context + error details: "Previous attempt failed with: {error}. Diagnose and fix."
4. Repeats up to 3 times.
5. After 3 failures: logs the issue, marks phase as `failed_skipped`, continues to next phase.

For parallel sub-agents within a phase (e.g., Build spawning frontend + backend agents): if one sub-agent fails, only that sub-agent is retried. Successful sub-agent results are preserved.

## Token Usage Tracking

The orchestrator tracks cumulative token usage across all agents and rounds. Displayed in the TUI dashboard footer and written to `.builder/logs/token-usage.json` at the end of execution. Provides per-phase and per-round breakdowns.

## TUI Dashboard

Live terminal UI built with `textual` showing real-time progress. The orchestrator pushes events to the dashboard via an async message queue (`asyncio.Queue`). The dashboard runs as a `textual` app in the main thread, while the orchestrator runs in a background asyncio task.

- **Header** — project name, current round/total, current phase
- **Phase tracker** — checklist of all 6 phases with status indicators (complete, running, pending)
- **Active agents** — live view of running agents with current activity descriptions
- **Log stream** — scrolling log of recent events with timestamps
- **Footer** — cumulative token usage, elapsed time, cancel hint (Ctrl+C)

## Project Structure

```
builder/
├── pyproject.toml
├── builder/
│   ├── __init__.py
│   ├── main.py              # Entry point, CLI wizard
│   ├── orchestrator.py      # Round loop, phase pipeline
│   ├── agents.py            # AgentManager, AgentConfig, AgentResult
│   ├── context.py           # ProjectContext, state management
│   ├── phases/
│   │   ├── __init__.py
│   │   ├── base.py          # BasePhase abstract class
│   │   ├── brainstorm.py
│   │   ├── research.py
│   │   ├── build.py
│   │   ├── verify.py
│   │   ├── test.py
│   │   └── improve.py
│   ├── dashboard/
│   │   ├── __init__.py
│   │   └── app.py           # Textual TUI dashboard
│   └── prompts/
│       ├── brainstorm.md
│       ├── research.md
│       ├── build.md
│       ├── verify.md
│       ├── test.md
│       └── improve.md
└── tests/
    ├── test_orchestrator.py
    ├── test_agents.py
    ├── test_context.py
    └── test_phases.py
```

## Dependencies

- `claude-code-sdk` (import: `claude_code_sdk`) — spawning Claude Code subagents. Note: the exact package name should be verified against the latest published SDK at implementation time. If unavailable, fall back to subprocess-based CLI invocation of `claude`.
- `textual` — TUI dashboard
- `inquirerpy` — interactive CLI wizard prompts
- `pydantic` — data models for config, state, agent results
- `asyncio` — async orchestration (stdlib)

## Design Decisions

- **Pipeline over DAG**: Sequential phases map naturally to the round-based model. Simpler to build, debug, and reason about. Can evolve to a DAG later if needed.
- **`.builder/` metadata directory**: Keeps orchestration state separate from project output. Serves as communication channel between phases and a build record.
- **Textual for TUI**: Full-featured TUI framework with proper resize, scrolling, and widget support — better than raw `rich.live` for a dashboard with multiple panels.
- **Self-healing over fail-fast**: Autonomous operation requires resilience. Passing error context on retry lets agents diagnose their own failures.
- **Prompt files as markdown**: Keeps system prompts readable, editable, and version-controlled separate from code. Loaded at runtime with Python string `.format()` for variable substitution (e.g., `{project_type}`, `{round_number}`). The orchestrator reads each `.md` file, substitutes variables, and prepends accumulated context files.
- **Git commit per round**: The orchestrator creates a git commit at the end of each round to provide a snapshot of progress. This enables diffing between rounds and recovery if a later round introduces regressions. If the working directory is not a git repo, the orchestrator runs `git init` before the first round. Commit message format: `builder: round N complete`. The `.builder/` directory is committed alongside project files (it serves as the build record).
- **No budget cap in v1**: Token usage is tracked and displayed but not capped. Adding an optional `--max-tokens` budget is a future enhancement. The wizard displays a note that long runs with many rounds will consume significant tokens.
