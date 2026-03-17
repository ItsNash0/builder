<div align="center">

# Builder

**Turn a sentence into a complete, working software project.**

Builder orchestrates AI agents through iterative cycles of brainstorming, research, building, verification, testing, and improvement — delivering production-ready code with zero human intervention.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-3776ab?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Claude Code SDK](https://img.shields.io/badge/powered%20by-Claude%20Code-cc785c?style=flat-square)](https://docs.anthropic.com/en/docs/claude-code)
[![License: MIT](https://img.shields.io/badge/license-MIT-green?style=flat-square)](LICENSE)

---

<img width="700" alt="Builder TUI Dashboard" src="https://github.com/user-attachments/assets/placeholder">

</div>

## How It Works

You describe what you want. Builder does the rest.

```
$ builder

  Builder - Autonomous AI Agent Orchestrator

? What would you like to build? An iOS/Android Othello game with AI opponent
? What type of project? Mobile App
? How many iteration rounds? (1-10) 3

  Summary:
  Mode:     New project
  Prompt:   An iOS/Android Othello game with AI opponent
  Type:     mobile_app
  Rounds:   3

? Start building? Yes
```

Builder then runs **autonomous iteration rounds**, each with 6 phases:

```
Round 1/3 ─────────────────────────────────────────────────

  ✓ Brainstorm    Product spec, features, architecture
  ✓ Research      Latest libraries, versions, patterns
  ✓ Build         Write all code, install deps, verify it runs
  ✓ Verify        Code review, security audit, run the app
  ✓ Test          Playwright E2E tests, unit tests, smoke tests
  ✓ Improve       Prioritized improvements for next round

  → git commit: "builder: round 1 complete"

Round 2/3 ─────────────────────────────────────────────────
  ...applies improvements, re-tests, iterates...

Round 3/3 ─────────────────────────────────────────────────
  ...final polish, delivery readiness checks...
```

At the end, you have a **complete, tested, documented project** with a README, setup instructions, and passing tests.

## Features

- **Fully autonomous** — describe your project, pick iteration rounds, walk away
- **6-phase pipeline** — brainstorm → research → build → verify → test → improve
- **Real testing** — Playwright browser testing, not just unit tests. Agents click buttons, fill forms, and interact with your app like a human
- **Self-healing** — failed phases retry up to 3 times with exponential backoff
- **Rate limit resilient** — automatic retry with jitter on API rate limits
- **Live TUI dashboard** — watch agents work in real-time with phase tracking, cost, and logs
- **Existing project support** — run on an existing codebase to fix bugs, add features, or improve quality
- **Latest versions** — agents verify latest library versions before coding (no stale dependencies)
- **CLAUDE.md generation** — creates project conventions file for future AI agent sessions
- **Git integration** — automatic commit after each phase for granular rollback
- **Resume support** — interrupted builds can be resumed from where they left off
- **Cost tracking** — real-time USD cost display in the dashboard

## Supported Project Types

| Type | Stack | Testing |
|------|-------|---------|
| **Web App** | Next.js + TypeScript | Playwright E2E + Vitest |
| **Mobile App** | React Native + Expo + SpacetimeDB + Clerk | Playwright (web mode) + Jest |
| **API / Backend** | FastAPI or Express + TypeScript | pytest/Vitest + httpx |
| **CLI Tool** | Python + Click/Typer | pytest |
| **Library** | Python or TypeScript | pytest/Vitest |

Stacks are chosen for **testability** — every project can be built, run, and verified entirely from the command line without emulators or manual browser interaction.

## Installation

### Prerequisites

- **Python 3.11+**
- **Claude Code CLI** — [install instructions](https://docs.anthropic.com/en/docs/claude-code)
- **Node.js 18+** (for web/mobile projects)

### Install with pipx (recommended)

```bash
pipx install git+https://github.com/ItsNash0/builder.git
```

This installs `builder` as an isolated CLI tool. [Install pipx](https://pipx.pypa.io/stable/installation/) if you don't have it.

### Install with pip

```bash
pip install git+https://github.com/ItsNash0/builder.git
```

### Install from source (for development)

```bash
git clone https://github.com/ItsNash0/builder.git
cd builder
pip install -e ".[dev]"
```

### Verify

```bash
builder --help
```

## Usage

### New Project

```bash
# Navigate to where you want the project created
mkdir my-app && cd my-app

# Run builder
builder
```

### Existing Project

```bash
# Navigate to your existing project
cd my-existing-app

# Run builder — it detects existing code automatically
builder

# Choose: Fix & improve, Add features, or Start fresh
```

### Options in the Wizard

| Option | Description |
|--------|-------------|
| **What to build** | Natural language description of your project |
| **Project type** | Web App, CLI Tool, API, Library, Mobile App, Other |
| **Iteration rounds** | 1–10 rounds (more rounds = higher quality, more tokens) |

## Architecture

```
builder/
├── main.py            # CLI wizard + dashboard launcher
├── orchestrator.py    # Round loop, phase dispatch, retry logic
├── agents.py          # Claude Code SDK wrapper, rate limit retry
├── context.py         # .builder/ state management, resume support
├── models.py          # Pydantic models for config, state, results
├── events.py          # Event system for dashboard updates
├── dashboard/
│   └── app.py         # Textual TUI with phase tracker + live log
├── phases/
│   ├── base.py        # Abstract base phase with prompt loading
│   ├── brainstorm.py  # Product spec generation
│   ├── research.py    # 3 parallel research agents
│   ├── build.py       # Code generation + verification
│   ├── verify.py      # Code review + runtime verification
│   ├── test.py        # E2E + unit testing with Playwright
│   └── improve.py     # Improvement suggestions (applied on final round)
└── prompts/
    └── *.md           # Phase-specific prompt templates
```

### Pipeline Flow

```
                    ┌─────────────────────────────────┐
                    │         Orchestrator             │
                    │   (manages rounds & retries)     │
                    └─────────────┬───────────────────┘
                                  │
              ┌───────────────────┼───────────────────┐
              │                   │                   │
         Round 1             Round 2             Round N
              │                   │                   │
    ┌─────────┴─────────┐        │                   │
    │                   │        ...                 ...
    ▼                   ▼
 Brainstorm ──→ Research (3 parallel agents)
    │               │
    ▼               ▼
  Build ──→ Verify ──→ Test ──→ Improve
    │          │         │         │
    └──────────┴─────────┴─────────┘
              git commit per phase
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run tests with verbose output
pytest -v

# Run a specific test file
pytest tests/test_agents.py
```

### Test Suite

| File | Tests | Coverage |
|------|-------|----------|
| `test_models.py` | 8 | Pydantic models, enums, serialization |
| `test_context.py` | 12 | State management, file I/O, resume |
| `test_agents.py` | 4 | Agent spawning, parallel execution, events |
| `test_orchestrator.py` | 5 | Round loop, phase dispatch, retry logic |
| `test_phases.py` | 13 | All 6 phases: run + validate |
| **Total** | **42** | |

## How Phases Work

### Brainstorm
Generates a detailed product spec: features, architecture, file structure, tech stack, and how-to-run instructions. For existing projects, analyzes the codebase first.

### Research
Spawns **3 parallel agents** focused on: library recommendations (with latest versions verified via `npm view`/`pip index`), design patterns, and common pitfalls.

### Build
The main coding agent. Writes all code, installs dependencies, starts the app, and verifies it actually runs. Creates a comprehensive README. On round 2+, applies improvements from the previous round.

### Verify
Code review + runtime verification. Uses **Playwright** to open the app in a real browser, take screenshots, and check for JavaScript errors. Runs static analysis. Fixes critical/high issues directly.

### Test
QA agent that tests like a human. Follows the README from scratch, runs the app, interacts with it via **Playwright** (clicks buttons, fills forms, navigates screens), writes E2E and unit tests, and fixes any broken code.

### Improve
Analyzes verification and test results. Produces a prioritized improvement list. On the **final round**, applies all P0/P1 fixes directly and does a delivery readiness check.

## Configuration

Builder stores state in `.builder/` in your project directory:

```
.builder/
├── config.json        # Build configuration
├── state.json         # Current progress (for resume)
├── token_usage.json   # Cost breakdown per round/phase
└── rounds/
    ├── 1/
    │   ├── brainstorm.md
    │   ├── research.md
    │   ├── verify.md
    │   ├── test.md
    │   └── improve.md
    └── 2/
        └── ...
```

## License

MIT
