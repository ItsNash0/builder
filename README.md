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

Builder then runs **autonomous iteration rounds**, each with 8 phases:

```
Round 1/3 ─────────────────────────────────────────────────

  ✓ Brainstorm    Product spec, features, architecture       (Opus)
  ✓ Research      Latest libraries, versions, patterns       (Opus × 3)
  ✓ Design        Design tokens, colors, typography, styles  (Opus)
  ✓ Setup         Scaffold, deps, Supabase config, CLAUDE.md (Sonnet)
  ✓ Build         Write all application code                 (Sonnet)
  ✓ Test          Playwright E2E + unit tests, fix failures  (Sonnet)
  ✓ Verify        User/Security/Quality multi-persona review (Opus × 3)
  ✓ Improve       Fix all issues, re-run tests               (Opus)

  → git commit: "builder: round 1 complete"

Round 2/3 ─────────────────────────────────────────────────
  ...applies improvements, re-tests, iterates...

Round 3/3 ─────────────────────────────────────────────────
  ...final polish, delivery readiness checks...
```

At the end, you have a **complete, tested, documented project** with a README, setup instructions, and passing tests.

## Features

- **Fully autonomous** — describe your project, pick iteration rounds, walk away
- **8-phase pipeline** — brainstorm → research → design → setup → build → test → verify → improve
- **Design system** — custom colors, typography, and component styles so UIs don't look AI-generated
- **Real testing** — Playwright browser testing, not just unit tests. Agents click buttons, fill forms, and interact with your app like a human
- **Supabase MCP integration** — agents can create tables, apply migrations, and test against your real Supabase project
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
| **Web App** | Next.js + Tailwind + shadcn/ui (pnpm) | Playwright E2E + Vitest |
| **Landing Page** | Astro + Tailwind CSS (pnpm) | Playwright E2E |
| **Mobile App** | Expo + React Native + Tamagui + Supabase | Playwright (web mode) + Jest |
| **API / Backend** | FastAPI + Supabase or Laravel | pytest + httpx / PHPUnit |
| **CLI Tool** | Python + Click/Typer | pytest |
| **Library** | Python or TypeScript | pytest/Vitest |

Stacks are opinionated for **speed and quality**. Every project uses pnpm, Supabase for backend (or Laravel for complex APIs), and can be tested from the CLI.

## Installation

### Prerequisites (required)

| Requirement | Why | Install |
|-------------|-----|---------|
| **Python 3.11+** | Builder itself is Python | [python.org](https://python.org) |
| **Claude Code CLI** | Builder spawns Claude Code subagents | [docs.anthropic.com](https://docs.anthropic.com/en/docs/claude-code) |
| **Node.js 18+** | For web/mobile/API projects | [nodejs.org](https://nodejs.org) |
| **pnpm** | Package manager for all JS/TS projects | `npm install -g pnpm` |
| **Lightpanda** | Headless browser for E2E testing (replaces Chromium) | [lightpanda.io](https://github.com/lightpanda-io/browser) |

### Optional (recommended)

| Requirement | Why | Install |
|-------------|-----|---------|
| **Supabase MCP** | Lets agents create tables, apply migrations, and test against your real Supabase project | [supabase-community/supabase-mcp](https://github.com/supabase-community/supabase-mcp) |
| **PHP 8.2+ & Composer** | Only if building Laravel backend projects | [php.net](https://php.net), [getcomposer.org](https://getcomposer.org) |

### Install Builder

**With pipx (recommended):**

```bash
pipx install git+https://github.com/ItsNash0/builder.git
```

[Install pipx](https://pipx.pypa.io/stable/installation/) if you don't have it.

**With pip:**

```bash
pip install git+https://github.com/ItsNash0/builder.git
```

**From source (for development):**

```bash
git clone https://github.com/ItsNash0/builder.git
cd builder
pip install -e ".[dev]"
```

### Setup Supabase MCP

Most web and mobile apps use Supabase for backend. Without the MCP, agents create schema SQL files and placeholder env vars but can't set up the actual database.

With the MCP, agents **directly create tables, apply migrations, get real credentials, and test API calls**:

1. Install: [supabase-community/supabase-mcp](https://github.com/supabase-community/supabase-mcp)
2. Add to Claude Code MCP config (`~/.claude/settings.json`)
3. Builder agents automatically detect and use it

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
├── orchestrator.py    # Round loop, phase dispatch, retry, rollback
├── agents.py          # Claude Code SDK wrapper, model routing, rate limit retry
├── context.py         # .builder/ state management, context priority, resume
├── models.py          # Pydantic models for config, state, results
├── events.py          # Event system for dashboard updates
├── error_memory.py    # Error pattern cache — agents learn from past failures
├── repomap.py         # Lightweight AST-based codebase map for agent context
├── dashboard/
│   └── app.py         # Textual TUI with phase tracker + live log
├── phases/
│   ├── base.py        # Abstract base with prompt loading, repo map, error memory
│   ├── brainstorm.py  # Product spec (or audit for existing projects)
│   ├── research.py    # 3 parallel research agents
│   ├── design.py      # Design tokens, colors, typography, component styles
│   ├── setup.py       # Scaffold, deps, Supabase config, CLAUDE.md
│   ├── build.py       # Application code only (UI, logic, routing)
│   ├── test.py        # E2E (Playwright + Lightpanda) + unit tests
│   ├── verify.py      # 3 parallel agents: user, security, quality review
│   └── improve.py     # Fix all issues, re-test, delivery readiness
└── prompts/
    └── *.md           # Phase-specific prompt templates
```

### Pipeline Flow

```
New project:     brainstorm → research → design → setup → build → test → verify → improve
                   (Opus)    (Opus ×3)  (Opus)  (Sonnet) (Sonnet) (Sonnet) (Opus ×3) (Opus)

Existing project: brainstorm → research → build → test → verify → improve
                   (audit)    (Opus ×3) (Sonnet) (Sonnet) (Opus ×3) (Opus)

Each phase: git commit  │  Up to 3 retries  │  Rollback on test/improve failure
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

### Brainstorm (Opus)
Generates a detailed product spec: features, architecture, file structure, Supabase schema, and how-to-run instructions. For existing projects, performs a deep audit instead — explores the codebase, tries to run it, and documents what works and what's broken.

### Research (Opus, 3 parallel agents)
Three agents research in parallel: library recommendations (with latest versions verified via `npm view`/`pip index`), design patterns and best practices, and common pitfalls and gotchas.

### Design (Opus) — *new projects only*
Creates a design system so the UI doesn't look AI-generated: custom color palette, typography choices, spacing tokens, component style guide, and framework-specific config (Tailwind/Tamagui). Produces `design-tokens.json`.

### Setup (Sonnet) — *new projects only*
Scaffolds the project, installs all dependencies, configures Supabase (schema, auth, RLS policies via MCP if available), creates `CLAUDE.md`, and verifies the foundation compiles and starts. No app code — just infrastructure.

### Build (Sonnet)
Writes all application code: UI, business logic, routing, Supabase integration. Follows the design system from the design phase. Runs a build-test loop until the app compiles and starts successfully. Creates README.

### Test (Sonnet)
QA agent that tests like a human using **Playwright + Lightpanda**. Follows the README from scratch, interacts with the UI (clicks, forms, navigation), tests Supabase auth/CRUD/real-time flows, writes E2E and unit tests, and fixes broken code.

### Verify (Opus, 3 parallel agents)
Three personas review the project simultaneously after tests pass:
- **User**: follows README, tests every feature end-to-end
- **Security**: checks for injection, hardcoded secrets, bad auth, vulnerable deps
- **Quality**: runs linters/type checking, verifies spec compliance, checks README accuracy

### Improve (Opus)
**Always fixes issues** — not just lists them. Applies all P0/P1/P2 fixes from verify and test, re-runs tests, and checks delivery readiness. On the final round, does a complete polish pass and ensures the project works out of the box.

## Configuration

Builder stores state in `.builder/` in your project directory:

```
.builder/
├── config.json          # Build configuration
├── state.json           # Current progress (for resume)
├── errors.json          # Error pattern memory (agents learn from failures)
├── specs/               # Brainstorm output per round
├── research/            # Research output per round
├── design/              # Design system output per round
├── setup/               # Setup report per round
├── testing/             # Test results per round
├── verification/        # Verification reports per round
├── improvements/        # Improvement reports per round
└── logs/
    └── token-usage.json # Cost breakdown per round/phase
```

## License

MIT
