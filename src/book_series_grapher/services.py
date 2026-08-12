from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import Any

from fastmcp import Client
from pydantic_ai import Agent

from .agents import build_extraction_agent, build_question_agent
from .domain import ChapterAnalysis
from .ingestion import ParsedChapter, split_chapters
from .settings import Settings


class BookProcessor:
    def __init__(self, settings: Settings | None = None, extraction_agent_factory: Callable[[Settings], Agent[None, ChapterAnalysis]] = build_extraction_agent) -> None:
        self.settings = settings or Settings()
        self._extraction_agent_factory = extraction_agent_factory
        self._tasks: set[asyncio.Task[None]] = set()

    async def _call_mcp(self, tool_name: str, arguments: dict[str, Any]) -> Any:
        async with Client(self.settings.mcp_url) as client:
            result = await client.call_tool(tool_name, arguments)
            return result.data

    async def submit(self, *, title: str, series_name: str | None, series_order: int | None, filename: str, content: bytes) -> dict[str, Any]:
        text = content.decode("utf-8")
        chapters = split_chapters(text)
        registration = await self._call_mcp("register_book", {"title": title, "series_name": series_name, "series_order": series_order, "source_filename": filename, "chapters": [{"sequence": chapter.sequence, "title": chapter.title, "text": chapter.text} for chapter in chapters]})
        book_id = registration["book_id"]
        task = asyncio.create_task(self._process(book_id=book_id, title=title, series_name=series_name, series_order=series_order, chapters=chapters))
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)
        return registration

    async def _process(self, *, book_id: str, title: str, series_name: str | None, series_order: int | None, chapters: list[ParsedChapter]) -> None:
        try:
            await self._call_mcp("set_book_status", {"book_id": book_id, "status": "processing"})
            agent = self._extraction_agent_factory(self.settings)
            async with agent:
                for chapter in chapters:
                    prompt = f"Book: {title}\nSeries: {series_name or '(standalone)'}\nSeries order: {series_order or 1}\nChapter {chapter.sequence}: {chapter.title}\n\nCHAPTER TEXT\n{chapter.text}"
                    result = await agent.run(prompt)
                    await self._call_mcp("store_chapter_analysis", {"book_id": book_id, "chapter_sequence": chapter.sequence, "analysis": result.output.model_dump(mode="json")})
            await self._call_mcp("set_book_status", {"book_id": book_id, "status": "completed"})
        except Exception as exc:
            await self._call_mcp("set_book_status", {"book_id": book_id, "status": "failed", "error": str(exc)[:4000]})

    async def status(self, book_id: str) -> dict[str, Any] | None:
        return await self._call_mcp("get_book_status", {"book_id": book_id})


class QuestionService:
    def __init__(self, settings: Settings | None = None, question_agent_factory: Callable[[Settings], Agent[None, str]] = build_question_agent) -> None:
        self.settings = settings or Settings()
        self._question_agent_factory = question_agent_factory

    async def ask(self, question: str, through_sequence: int | None) -> dict[str, Any]:
        cutoff_text = str(through_sequence) if through_sequence is not None else "latest available story position (the user explicitly requested no spoiler cutoff)"
        agent = self._question_agent_factory(self.settings)
        prompt = f"Hard spoiler cutoff: {cutoff_text}.\nQuestion: {question}\nWhen calling any temporal MCP tool, pass this exact cutoff if numeric."
        async with agent:
            result = await agent.run(prompt)
        return {"answer": result.output, "through_sequence": through_sequence}
