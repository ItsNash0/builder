import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from builder.agents import AgentManager
from builder.events import AgentFinished, AgentSpawned
from builder.models import AgentConfig, AgentResult


@pytest.fixture
def event_queue():
    return asyncio.Queue()


@pytest.fixture
def manager(event_queue):
    return AgentManager(event_queue=event_queue)


@pytest.fixture
def sample_config():
    return AgentConfig(
        system_prompt="You are a test agent",
        context_files=[],
        working_directory="/tmp/test",
        timeout=60,
    )


@pytest.mark.asyncio
async def test_spawn_agent_success(manager, sample_config):
    from claude_code_sdk import AssistantMessage, ResultMessage, TextBlock

    text_block = MagicMock(spec=TextBlock)
    text_block.text = "Hello"

    assistant_msg = MagicMock(spec=AssistantMessage)
    assistant_msg.content = [text_block]

    result_msg = MagicMock(spec=ResultMessage)
    result_msg.total_cost_usd = 0.01

    mock_messages = [assistant_msg, result_msg]

    async def mock_query(**kwargs):
        for msg in mock_messages:
            yield msg

    with patch("builder.agents.query", side_effect=mock_query):
        result = await manager.spawn_agent(sample_config, prompt="Test task")

    assert result.success is True
    assert "Hello" in result.output


@pytest.mark.asyncio
async def test_spawn_agent_error(manager, sample_config):
    async def mock_query(**kwargs):
        raise RuntimeError("Agent crashed")
        yield  # make it an async generator

    with patch("builder.agents.query", side_effect=mock_query):
        result = await manager.spawn_agent(sample_config, prompt="Test")

    assert result.success is False
    assert "Agent crashed" in result.error


@pytest.mark.asyncio
async def test_spawn_parallel(manager):
    configs = [
        AgentConfig(system_prompt="Agent 1", context_files=[], working_directory="/tmp"),
        AgentConfig(system_prompt="Agent 2", context_files=[], working_directory="/tmp"),
    ]

    async def mock_spawn(config, prompt=""):
        return AgentResult(success=True, output=f"Result from {config.system_prompt}", token_usage=100)

    manager.spawn_agent = AsyncMock(side_effect=mock_spawn)
    results = await manager.spawn_parallel(configs)

    assert len(results) == 2
    assert all(r.success for r in results)


@pytest.mark.asyncio
async def test_events_emitted_on_spawn(manager, sample_config, event_queue):
    async def mock_query(**kwargs):
        msg = MagicMock(__class__=MagicMock(__name__="ResultMessage"), total_cost_usd=0.01)
        yield msg

    with patch("builder.agents.query", side_effect=mock_query):
        await manager.spawn_agent(sample_config, prompt="Test")

    events = []
    while not event_queue.empty():
        events.append(await event_queue.get())

    event_types = [type(e).__name__ for e in events]
    assert "AgentSpawned" in event_types
    assert "AgentFinished" in event_types
