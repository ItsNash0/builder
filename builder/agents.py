import asyncio
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
)
from builder.models import AgentConfig, AgentResult


class AgentManager:
    def __init__(self, event_queue: asyncio.Queue):
        self.event_queue = event_queue

    async def _emit(self, event) -> None:
        await self.event_queue.put(event)

    async def spawn_agent(
        self, config: AgentConfig, prompt: str = ""
    ) -> AgentResult:
        """Spawn a single Claude Code subagent.

        Args:
            config: Agent configuration (system_prompt used as system prompt)
            prompt: The user-facing prompt/task (what to do). If empty, uses system_prompt.
        """
        agent_id = str(uuid.uuid4())[:8]

        await self._emit(AgentSpawned(
            agent_id=agent_id,
            phase_name="",
            description=config.system_prompt[:80],
        ))

        user_prompt = prompt if prompt else "Execute your task as described in the system prompt."
        output_parts: list[str] = []
        token_usage = 0

        options = ClaudeCodeOptions(
            system_prompt=config.system_prompt,
            cwd=Path(config.working_directory),
            permission_mode="bypassPermissions",
            max_turns=50,
        )

        try:
            async for message in query(prompt=user_prompt, options=options):
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
                        # Approximate tokens from cost (rough estimate).
                        # The SDK does not expose raw token counts directly.
                        token_usage = int(message.total_cost_usd * 100000)

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
            result = AgentResult(
                success=False,
                output="",
                error=f"Process failed with exit code: {e.exit_code}",
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
        self, configs: list[AgentConfig], prompts: list[str] | None = None
    ) -> list[AgentResult]:
        """Spawn multiple agents concurrently."""
        if prompts is None:
            prompts = [""] * len(configs)
        tasks = [
            self.spawn_agent(config, prompt=prompt)
            for config, prompt in zip(configs, prompts)
        ]
        return await asyncio.gather(*tasks)
