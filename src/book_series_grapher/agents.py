from __future__ import annotations

from pydantic_ai import Agent
from pydantic_ai.mcp import MCPToolset

from .domain import ChapterAnalysis
from .settings import Settings

_READ_TOOLS = {"find_characters", "get_character_status", "get_character_timeline", "get_interactions", "get_relationship_history", "get_character_knowledge", "search_story", "get_book_status"}


def _read_only_mcp(settings: Settings) -> MCPToolset:
    toolset = MCPToolset(settings.mcp_url)
    return toolset.filtered(lambda _ctx, tool_def: tool_def.name in _READ_TOOLS)


def build_extraction_agent(settings: Settings) -> Agent[None, ChapterAnalysis]:
    return Agent(
        settings.agent_model_name(extraction=True),
        output_type=ChapterAnalysis,
        model_settings=settings.agent_model_settings(extraction=True),
        toolsets=[_read_only_mcp(settings)],
        instructions=(
            "Extract only facts supported by the supplied chapter. Return a complete ChapterAnalysis. Declare every referenced character in characters, using a chapter-local ref. Track aliases, character events, state changes, interactions and all participants, relationship changes, and what individual characters learn. Do not give a character knowledge merely because the reader learned it. Use MCP lookup tools when needed to preserve canonical identity with earlier chapters. Keep source excerpts short and verbatim only when useful for traceability."
        ),
    )


def build_question_agent(settings: Settings) -> Agent[None, str]:
    return Agent(
        settings.agent_model_name(),
        model_settings=settings.agent_model_settings(),
        toolsets=[_read_only_mcp(settings)],
        instructions=(
            "Answer questions using the MCP knowledge tools. Respect through_sequence as a hard spoiler boundary. Never mention or use facts after that boundary. Distinguish reader knowledge from what a character personally knows, and distinguish co-presence/interaction from inferred relationship. If evidence is missing or ambiguous, say so instead of inventing a fact."
        ),
    )
