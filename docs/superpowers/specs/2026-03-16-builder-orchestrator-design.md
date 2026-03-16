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

No further interaction is required until the final output is delivered.

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
- On the final round: applies improvements directly instead of deferring.
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

Tracks execution progress:

```json
{
  "current_round": 2,
  "total_rounds": 3,
  "current_phase": "build",
  "phase_status": "in_progress",
  "retry_count": 0,
  "completed_phases": ["brainstorm", "research"]
}
```

### Context Flow

- Each agent receives: the user's original prompt, the current round's spec, and outputs from prior phases in the current round.
- Round 2+: agents also receive the previous round's improvement suggestions.
- The orchestrator assembles each agent's prompt from relevant `.builder/` files.

## Claude Code SDK Layer

### AgentManager

```python
class AgentManager:
    async def spawn_agent(self, config: AgentConfig) -> AgentSession
    async def spawn_parallel(self, configs: list[AgentConfig]) -> list[AgentSession]
    async def run_with_retry(self, config: AgentConfig, max_retries: int = 3) -> AgentResult
```

### AgentConfig

- `system_prompt` — role and instructions for the phase
- `context_files` — list of `.builder/` files to include
- `allowed_tools` — tools the agent can use (file write, bash, web search, etc.)
- `working_directory` — where the agent operates

### AgentResult

- `success: bool`
- `output: str` — agent's final response
- `files_created: list[str]` — files written by the agent
- `error: str | None` — error details if failed

## Self-Healing & Error Recovery

1. Agent runs and fails (error, crash, or phase validation failure).
2. Orchestrator captures the error.
3. Respawns agent with original context + error details: "Previous attempt failed with: {error}. Diagnose and fix."
4. Repeats up to 3 times.
5. After 3 failures: logs the issue, marks phase as `failed_skipped`, continues to next phase.

## TUI Dashboard

Live terminal UI built with `textual` showing real-time progress:

- **Header** — project name, current round/total, current phase
- **Phase tracker** — checklist of all 6 phases with status indicators (complete, running, pending)
- **Active agents** — live view of running agents with current activity descriptions
- **Log stream** — scrolling log of recent events with timestamps

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

- `claude_agent_sdk` — spawning Claude Code subagents
- `textual` — TUI dashboard
- `inquirerpy` — interactive CLI wizard prompts
- `pydantic` — data models for config, state, agent results
- `asyncio` — async orchestration (stdlib)

## Design Decisions

- **Pipeline over DAG**: Sequential phases map naturally to the round-based model. Simpler to build, debug, and reason about. Can evolve to a DAG later if needed.
- **`.builder/` metadata directory**: Keeps orchestration state separate from project output. Serves as communication channel between phases and a build record.
- **Textual for TUI**: Full-featured TUI framework with proper resize, scrolling, and widget support — better than raw `rich.live` for a dashboard with multiple panels.
- **Self-healing over fail-fast**: Autonomous operation requires resilience. Passing error context on retry lets agents diagnose their own failures.
- **Prompt files as markdown**: Keeps system prompts readable, editable, and version-controlled separate from code.
