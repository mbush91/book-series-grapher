from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator

from fastmcp import FastMCP

from .db import init_db, make_engine
from .domain import ChapterAnalysis
from .repository import StoryRepository
from .settings import Settings

settings = Settings()
engine = make_engine(settings)

mcp = FastMCP(
    "Book Series Grapher",
    instructions=(
        "Temporal, spoiler-safe book-series knowledge tools. For every reader-facing lookup, use the reader's story cutoff as through_sequence and never use facts after it. Character interactions, relationship changes, and character-specific knowledge are distinct concepts; consult the matching tools rather than guessing."
    ),
)


@asynccontextmanager
async def _repo() -> AsyncIterator[StoryRepository]:
    async with engine.begin() as connection:
        yield StoryRepository(connection)


@mcp.tool
async def register_book(title: str, chapters: list[dict[str, Any]], series_name: str | None = None, series_order: int | None = None, source_filename: str | None = None) -> dict[str, Any]:
    """Register a book and its ordered chapter text before chapter extraction begins."""
    async with _repo() as repo:
        return await repo.register_book(title=title, chapters=chapters, series_name=series_name, series_order=series_order, source_filename=source_filename)


@mcp.tool
async def set_book_status(book_id: str, status: str, error: str | None = None) -> dict[str, Any]:
    """Set ingestion status for a registered book (queued, processing, completed, failed)."""
    async with _repo() as repo:
        return await repo.set_book_status(book_id, status, error)


@mcp.tool
async def get_book_status(book_id: str) -> dict[str, Any] | None:
    """Get ingestion status and any processing error for a book."""
    async with _repo() as repo:
        return await repo.get_book_status(book_id)


@mcp.tool
async def store_chapter_analysis(book_id: str, chapter_sequence: int, analysis: ChapterAnalysis) -> dict[str, Any]:
    """Transactionally replace extracted temporal facts for one chapter with validated analysis."""
    async with _repo() as repo:
        return await repo.store_chapter_analysis(book_id=book_id, chapter_sequence=chapter_sequence, analysis=analysis)


@mcp.tool
async def find_characters(query: str, series_name: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
    """Resolve canonical characters and aliases. Use this when a name may be ambiguous or aliased."""
    async with _repo() as repo:
        return await repo.find_characters(query, series_name, limit)


@mcp.tool
async def get_character_status(name: str, through_sequence: int, series_name: str | None = None) -> dict[str, Any]:
    """Return the latest known state for each character attribute at or before the spoiler cutoff."""
    async with _repo() as repo:
        return await repo.character_status(name, through_sequence, series_name)


@mcp.tool
async def get_character_timeline(name: str, through_sequence: int, series_name: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    """Return a character's events/interactions through a story position, newest first."""
    async with _repo() as repo:
        return await repo.character_timeline(name, through_sequence, series_name, limit)


@mcp.tool
async def get_interactions(name: str, through_sequence: int, series_name: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    """Return interactions involving a character, including all participants, through the cutoff."""
    async with _repo() as repo:
        return await repo.interactions(name, through_sequence, series_name, limit)


@mcp.tool
async def get_relationship_history(name_a: str, name_b: str, through_sequence: int, series_name: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    """Return explicit relationship changes between two characters through the cutoff."""
    async with _repo() as repo:
        return await repo.relationship_history(name_a, name_b, through_sequence, series_name, limit)


@mcp.tool
async def get_character_knowledge(name: str, through_sequence: int, series_name: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
    """Return facts a character personally knows/believes through the cutoff, not reader omniscience."""
    async with _repo() as repo:
        return await repo.character_knowledge(name, through_sequence, series_name, limit)


@mcp.tool
async def search_story(query: str, through_sequence: int, limit: int = 20) -> list[dict[str, Any]]:
    """Lexically search chapter text while strictly excluding text after the spoiler cutoff."""
    async with _repo() as repo:
        return await repo.search_story(query, through_sequence, limit)


def main() -> None:
    asyncio.run(init_db(engine))
    mcp.run(transport="http", host=settings.mcp_host, port=settings.mcp_port)


if __name__ == "__main__":
    main()
