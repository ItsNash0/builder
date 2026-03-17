import asyncio
import random
import uuid
from pathlib import Path

from claude_code_sdk import (
    query,
    ClaudeCodeOptions,
    AssistantMessage,
    ResultMessage,
    TextBlock,
    ToolUseBlock,
    CLINotFoundError,
    ProcessError,
)

from builder.events import (
    AgentSpawned,
    AgentOutput,
    AgentFinished,
    RetryAttempt,
    LogMessage,
    CostUpdate,
)
from builder.models import AgentConfig, AgentResult


# Monkeypatch the SDK's message parser to handle unknown message types
# (e.g. rate_limit_event) gracefully instead of raising MessageParseError.
# The SDK kills the async generator on unknown types, which is unrecoverable.
import claude_code_sdk._internal.message_parser as _mp
import claude_code_sdk._internal.client as _client

_original_parse_message = _mp.parse_message


def _patched_parse_message(data: dict):
    try:
        return _original_parse_message(data)
    except Exception as e:
        if "Unknown message type" in str(e):
            return None
        raise


# Patch both the module and the client's local reference
_mp.parse_message = _patched_parse_message
_client.parse_message = _patched_parse_message


# Tool scoping per phase type — restrict what agents can do
PHASE_TOOL_SCOPES = {
    "brainstorm": [
        "Read", "Glob", "Grep", "Bash(read-only commands)",
    ],
    "research": [
        "Read", "Glob", "Grep", "Bash", "WebSearch", "WebFetch",
    ],
    "design": [
        "Read", "Glob", "Grep", "Bash", "Write",
    ],
    "setup": None,   # Full access — needs to scaffold, install, configure
    "build": None,   # Full access — writes all app code
    "test": None,    # Full access — runs app, writes & runs tests
    "verify": None,  # Full access — runs app, fixes issues
    "improve": None, # Full access — fixes everything
}

# Phase-dependent max_turns — brainstorm needs few, build needs many
PHASE_MAX_TURNS = {
    "brainstorm": 25,
    "research": 30,
    "design": 30,
    "setup": 75,
    "build": 100,
    "test": 75,
    "verify": 50,
    "improve": 75,
}

# Rate limit retry config
MAX_SPAWN_RETRIES = 5
BASE_RETRY_DELAY = 2.0   # seconds
MAX_RETRY_DELAY = 120.0  # seconds

# Per-phase model routing — Opus for creative/judgment, Sonnet for coding/testing
PHASE_MODEL = {
    "brainstorm": None,              # Opus — creative product design
    "research": None,                # Opus — deep analysis
    "design": None,                  # Opus — creative design decisions
    "setup": "claude-sonnet-4-6",    # Sonnet — scaffolding, deps, config
    "build": "claude-sonnet-4-6",    # Sonnet — fast, great at coding
    "test": "claude-sonnet-4-6",     # Sonnet — fast, great at testing
    "verify": None,                  # Opus — judgment, security, quality
    "improve": None,                 # Opus — architectural fix decisions
}

# Fallback model chain (when primary keeps failing)
MODEL_FALLBACK_CHAIN = [
    None,                    # Default model
    "claude-sonnet-4-6",    # Fallback
]
FALLBACK_AFTER_FAILURES = 3


def _is_rate_limit_error(error: Exception) -> bool:
    """Check if an error is a rate limit / transient error worth retrying."""
    msg = str(error).lower()
    return any(kw in msg for kw in [
        "rate_limit", "rate limit", "429", "overloaded",
        "too many requests", "capacity", "server_error",
        "500", "502", "503", "529",
    ])


class AgentManager:
    def __init__(self, event_queue: asyncio.Queue):
        self.event_queue = event_queue
        self.total_cost_usd: float = 0.0
        self._consecutive_failures = 0

    async def _emit(self, event) -> None:
        await self.event_queue.put(event)

    def _get_model(self, phase_name: str = "") -> str | None:
        """Get model for a phase. Uses phase routing first, then fallback chain on repeated failures."""
        # On repeated failures, force fallback regardless of phase preference
        if self._consecutive_failures >= FALLBACK_AFTER_FAILURES:
            return MODEL_FALLBACK_CHAIN[-1]
        # Use per-phase model routing
        if phase_name and phase_name in PHASE_MODEL:
            return PHASE_MODEL[phase_name]
        return MODEL_FALLBACK_CHAIN[0]

    async def spawn_agent(
        self, config: AgentConfig, prompt: str = "", phase_name: str = ""
    ) -> AgentResult:
        for attempt in range(1, MAX_SPAWN_RETRIES + 1):
            model = self._get_model(phase_name)
            if model and self._consecutive_failures >= FALLBACK_AFTER_FAILURES:
                await self._emit(LogMessage(
                    message=f"Switching to fallback model ({model}) after {self._consecutive_failures} failures",
                    level="warning",
                ))

            result = await self._spawn_agent_once(config, prompt, phase_name, model=model)

            if result.success:
                self._consecutive_failures = 0
                return result

            self._consecutive_failures += 1

            if result.error and _is_rate_limit_error(Exception(result.error)):
                if attempt < MAX_SPAWN_RETRIES:
                    delay = min(BASE_RETRY_DELAY * (2 ** (attempt - 1)), MAX_RETRY_DELAY)
                    jitter = random.uniform(0, delay * 0.5)
                    wait_time = delay + jitter

                    await self._emit(RetryAttempt(
                        phase_name=phase_name,
                        attempt=attempt,
                        max_retries=MAX_SPAWN_RETRIES,
                        reason=f"Rate limited. Waiting {wait_time:.0f}s before retry...",
                    ))
                    await asyncio.sleep(wait_time)
                    continue

            return result

        return result

    async def _spawn_agent_once(
        self, config: AgentConfig, prompt: str = "", phase_name: str = "",
        model: str | None = None,
    ) -> AgentResult:
        agent_id = str(uuid.uuid4())[:8]

        await self._emit(AgentSpawned(
            agent_id=agent_id,
            phase_name=phase_name,
            description=config.system_prompt[:80],
        ))

        user_prompt = prompt if prompt else "Execute your task as described in the system prompt."
        output_parts: list[str] = []
        token_usage = 0
        cost_usd = 0.0

        max_turns = PHASE_MAX_TURNS.get(phase_name, 50)

        options = ClaudeCodeOptions(
            system_prompt=config.system_prompt,
            cwd=Path(config.working_directory),
            permission_mode="bypassPermissions",
            max_turns=max_turns,
            **({"model": model} if model else {}),
        )

        try:
            async for message in query(prompt=user_prompt, options=options):
                if message is None:
                    continue
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            output_parts.append(block.text)
                            await self._emit(AgentOutput(
                                agent_id=agent_id,
                                text=block.text[:200],
                            ))
                        elif isinstance(block, ToolUseBlock):
                            await self._emit(AgentOutput(
                                agent_id=agent_id,
                                text=f"Using tool: {block.name}",
                            ))
                elif isinstance(message, ResultMessage):
                    if message.total_cost_usd:
                        cost_usd = message.total_cost_usd
                        self.total_cost_usd += cost_usd
                        # Approximate tokens from cost (rough estimate).
                        token_usage = int(cost_usd * 100000)
                        await self._emit(CostUpdate(total_cost_usd=self.total_cost_usd))

            result = AgentResult(
                success=True,
                output="\n".join(output_parts),
                files_created=[],
                token_usage=token_usage,
            )
        except CLINotFoundError:
            result = AgentResult(
                success=False,
                output="",
                error="Claude Code CLI not found. Please install it first.",
                token_usage=0,
            )
        except ProcessError as e:
            error_msg = f"Process failed with exit code: {e.exit_code}"
            result = AgentResult(
                success=False,
                output="",
                error=error_msg,
                token_usage=0,
            )
        except Exception as e:
            result = AgentResult(
                success=False,
                output="",
                error=str(e),
                token_usage=0,
            )

        await self._emit(AgentFinished(
            agent_id=agent_id,
            success=result.success,
            token_usage=result.token_usage,
        ))

        return result

    async def spawn_parallel(
        self, configs: list[AgentConfig], prompts: list[str] | None = None, phase_name: str = ""
    ) -> list[AgentResult]:
        """Spawn multiple agents concurrently."""
        if prompts is None:
            prompts = [""] * len(configs)
        tasks = [
            self.spawn_agent(config, prompt=prompt, phase_name=phase_name)
            for config, prompt in zip(configs, prompts)
        ]
        return await asyncio.gather(*tasks)
