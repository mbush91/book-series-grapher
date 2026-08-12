from __future__ import annotations

import re
import uuid
from typing import Any

from sqlalchemy import delete, select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncConnection

from .db import Book, Chapter, Character, CharacterAlias, CharacterEvent, CharacterState, Interaction, InteractionParticipant, KnowledgeFact, RelationshipEvent, StoryChunk
from .domain import ChapterAnalysis


def _key(value: str | None) -> str:
    if not value:
        return "__standalone__"
    return re.sub(r"\s+", " ", value.strip().casefold())


def _story_sequence(series_order: int | None, chapter_sequence: int) -> int:
    return (series_order or 1) * 1_000_000 + chapter_sequence


class StoryRepository:
    def __init__(self, connection: AsyncConnection):
        self.connection = connection

    async def register_book(self, *, title: str, chapters: list[dict[str, Any]], series_name: str | None = None, series_order: int | None = None, source_filename: str | None = None) -> dict[str, Any]:
        book_id = uuid.uuid4()
        series_key = _key(series_name or title)
        await self.connection.execute(insert(Book).values(id=book_id, title=title, series_name=series_name, series_key=series_key, series_order=series_order, source_filename=source_filename, status="queued"))
        for chapter in chapters:
            story_sequence = _story_sequence(series_order, int(chapter["sequence"]))
            chapter_id = uuid.uuid4()
            await self.connection.execute(insert(Chapter).values(id=chapter_id, book_id=book_id, chapter_sequence=int(chapter["sequence"]), story_sequence=story_sequence, title=str(chapter["title"]), text=str(chapter["text"])))
            await self.connection.execute(insert(StoryChunk).values(id=uuid.uuid4(), chapter_id=chapter_id, story_sequence=story_sequence, text=str(chapter["text"])))
        return {"book_id": str(book_id), "status": "queued", "chapter_count": len(chapters)}

    async def set_book_status(self, book_id: str, status: str, error: str | None = None) -> dict[str, Any]:
        await self.connection.execute(update(Book).where(Book.id == uuid.UUID(book_id)).values(status=status, error=error))
        return {"book_id": book_id, "status": status, "error": error}

    async def get_book_status(self, book_id: str) -> dict[str, Any] | None:
        result = await self.connection.execute(select(Book.id, Book.title, Book.status, Book.error).where(Book.id == uuid.UUID(book_id)))
        row = result.mappings().first()
        if not row:
            return None
        return {**dict(row), "id": str(row["id"])}

    async def _resolve_or_create_character(self, *, series_key: str, canonical_name: str, aliases: list[str], description: str | None) -> uuid.UUID:
        candidate_keys = {_key(canonical_name), *(_key(alias) for alias in aliases)}
        result = await self.connection.execute(select(Character.id).outerjoin(CharacterAlias, CharacterAlias.character_id == Character.id).where(Character.series_key == series_key, (Character.canonical_key.in_(candidate_keys)) | (CharacterAlias.alias_key.in_(candidate_keys))).limit(1))
        existing = result.scalar_one_or_none()
        if existing:
            character_id = existing
            if description:
                await self.connection.execute(update(Character).where(Character.id == character_id).values(description=description))
        else:
            character_id = uuid.uuid4()
            await self.connection.execute(insert(Character).values(id=character_id, series_key=series_key, canonical_name=canonical_name, canonical_key=_key(canonical_name), description=description))
        for alias in {canonical_name, *aliases}:
            await self.connection.execute(insert(CharacterAlias).values(id=uuid.uuid4(), character_id=character_id, series_key=series_key, alias=alias, alias_key=_key(alias)).on_conflict_do_nothing(index_elements=["series_key", "alias_key"]))
        return character_id

    async def store_chapter_analysis(self, *, book_id: str, chapter_sequence: int, analysis: ChapterAnalysis) -> dict[str, Any]:
        chapter_result = await self.connection.execute(select(Chapter.id, Chapter.story_sequence, Book.series_key).join(Book, Book.id == Chapter.book_id).where(Chapter.book_id == uuid.UUID(book_id), Chapter.chapter_sequence == chapter_sequence))
        chapter = chapter_result.mappings().one()
        chapter_id, story_sequence, series_key = chapter["id"], chapter["story_sequence"], chapter["series_key"]
        interaction_ids_result = await self.connection.execute(select(Interaction.id).where(Interaction.chapter_id == chapter_id))
        interaction_ids = list(interaction_ids_result.scalars())
        if interaction_ids:
            await self.connection.execute(delete(InteractionParticipant).where(InteractionParticipant.interaction_id.in_(interaction_ids)))
        for model in (CharacterEvent, CharacterState, RelationshipEvent, KnowledgeFact, Interaction):
            await self.connection.execute(delete(model).where(model.chapter_id == chapter_id))

        ref_map: dict[str, uuid.UUID] = {}
        for character in analysis.characters:
            ref_map[character.ref] = await self._resolve_or_create_character(series_key=series_key, canonical_name=character.canonical_name, aliases=character.aliases, description=character.description)
        await self.connection.execute(update(Chapter).where(Chapter.id == chapter_id).values(summary=analysis.summary))

        for event in analysis.events:
            await self.connection.execute(insert(CharacterEvent).values(id=uuid.uuid4(), chapter_id=chapter_id, character_id=ref_map[event.character_ref], story_sequence=story_sequence, event_type=event.event_type, summary=event.summary, source_excerpt=event.source_excerpt))
        for state in analysis.states:
            await self.connection.execute(insert(CharacterState).values(id=uuid.uuid4(), chapter_id=chapter_id, character_id=ref_map[state.character_ref], story_sequence=story_sequence, attribute=state.attribute, value=state.value, confidence=state.confidence, source_excerpt=state.source_excerpt))
        for interaction in analysis.interactions:
            interaction_id = uuid.uuid4()
            await self.connection.execute(insert(Interaction).values(id=interaction_id, chapter_id=chapter_id, story_sequence=story_sequence, interaction_type=interaction.interaction_type, summary=interaction.summary, significance=interaction.significance, source_excerpt=interaction.source_excerpt))
            for participant in interaction.participants:
                await self.connection.execute(insert(InteractionParticipant).values(interaction_id=interaction_id, character_id=ref_map[participant.character_ref], role=participant.role, disposition=participant.disposition))
        for relation in analysis.relationships:
            await self.connection.execute(insert(RelationshipEvent).values(id=uuid.uuid4(), chapter_id=chapter_id, character_a_id=ref_map[relation.character_a_ref], character_b_id=ref_map[relation.character_b_ref], story_sequence=story_sequence, relationship_type=relation.relationship_type, value=relation.value, summary=relation.summary, source_excerpt=relation.source_excerpt))
        for fact in analysis.knowledge:
            await self.connection.execute(insert(KnowledgeFact).values(id=uuid.uuid4(), chapter_id=chapter_id, character_id=ref_map[fact.character_ref], learned_from_character_id=(ref_map[fact.learned_from_character_ref] if fact.learned_from_character_ref else None), story_sequence=story_sequence, fact=fact.fact, certainty=fact.certainty, source_excerpt=fact.source_excerpt))
        return {"book_id": book_id, "chapter_sequence": chapter_sequence, "story_sequence": story_sequence, "characters": len(ref_map), "interactions": len(analysis.interactions)}

    async def find_characters(self, query: str, series_name: str | None = None, limit: int = 10) -> list[dict[str, Any]]:
        params = {"query": f"%{query}%", "series_key": _key(series_name) if series_name else None, "limit": limit}
        result = await self.connection.execute(text("""
            SELECT DISTINCT c.id::text AS id, c.canonical_name, c.description
            FROM characters c LEFT JOIN character_aliases a ON a.character_id = c.id
            WHERE (:series_key IS NULL OR c.series_key = :series_key)
              AND (c.canonical_name ILIKE :query OR a.alias ILIKE :query)
            ORDER BY c.canonical_name LIMIT :limit
        """), params)
        return [dict(row) for row in result.mappings().all()]

    async def character_timeline(self, name: str, through_sequence: int, series_name: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        params = {"name": _key(name), "series_key": _key(series_name) if series_name else None, "through_sequence": through_sequence, "limit": limit}
        result = await self.connection.execute(text("""
            WITH target AS (
                SELECT DISTINCT c.id FROM characters c LEFT JOIN character_aliases a ON a.character_id = c.id
                WHERE (:series_key IS NULL OR c.series_key = :series_key)
                  AND (c.canonical_key = :name OR a.alias_key = :name) LIMIT 1
            ), timeline AS (
                SELECT e.story_sequence, ch.title AS chapter_title, 'event' AS kind, e.event_type AS type, e.summary, e.source_excerpt
                FROM character_events e JOIN target t ON t.id = e.character_id JOIN chapters ch ON ch.id = e.chapter_id
                WHERE e.story_sequence <= :through_sequence
                UNION ALL
                SELECT i.story_sequence, ch.title, 'interaction', i.interaction_type, i.summary, i.source_excerpt
                FROM interactions i JOIN interaction_participants ip ON ip.interaction_id = i.id JOIN target t ON t.id = ip.character_id JOIN chapters ch ON ch.id = i.chapter_id
                WHERE i.story_sequence <= :through_sequence
            ) SELECT * FROM timeline ORDER BY story_sequence DESC LIMIT :limit
        """), params)
        return [dict(row) for row in result.mappings().all()]

    async def character_status(self, name: str, through_sequence: int, series_name: str | None = None) -> dict[str, Any]:
        params = {"name": _key(name), "series_key": _key(series_name) if series_name else None, "through_sequence": through_sequence}
        result = await self.connection.execute(text("""
            WITH target AS (
                SELECT DISTINCT c.id, c.canonical_name FROM characters c LEFT JOIN character_aliases a ON a.character_id = c.id
                WHERE (:series_key IS NULL OR c.series_key = :series_key) AND (c.canonical_key = :name OR a.alias_key = :name) LIMIT 1
            ), latest AS (
                SELECT DISTINCT ON (s.attribute) s.attribute, s.value, s.confidence, s.story_sequence
                FROM character_states s JOIN target t ON t.id = s.character_id
                WHERE s.story_sequence <= :through_sequence ORDER BY s.attribute, s.story_sequence DESC
            ) SELECT (SELECT canonical_name FROM target) AS canonical_name,
              COALESCE(jsonb_object_agg(latest.attribute, latest.value) FILTER (WHERE latest.attribute IS NOT NULL), '{}'::jsonb) AS state FROM latest
        """), params)
        row = result.mappings().one()
        return {"canonical_name": row["canonical_name"], "through_sequence": through_sequence, "state": row["state"] or {}}

    async def interactions(self, name: str, through_sequence: int, series_name: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        params = {"name": _key(name), "series_key": _key(series_name) if series_name else None, "through_sequence": through_sequence, "limit": limit}
        result = await self.connection.execute(text("""
            WITH target AS (
                SELECT DISTINCT c.id FROM characters c LEFT JOIN character_aliases a ON a.character_id = c.id
                WHERE (:series_key IS NULL OR c.series_key = :series_key) AND (c.canonical_key = :name OR a.alias_key = :name) LIMIT 1
            ), matching AS (
                SELECT DISTINCT i.id, i.story_sequence, i.interaction_type, i.summary, i.significance, i.source_excerpt, ch.title AS chapter_title
                FROM interactions i JOIN interaction_participants mine ON mine.interaction_id = i.id JOIN target t ON t.id = mine.character_id JOIN chapters ch ON ch.id = i.chapter_id
                WHERE i.story_sequence <= :through_sequence ORDER BY i.story_sequence DESC LIMIT :limit
            ) SELECT m.*, COALESCE(jsonb_agg(jsonb_build_object('name', c.canonical_name, 'role', ip.role, 'disposition', ip.disposition) ORDER BY c.canonical_name), '[]'::jsonb) AS participants
            FROM matching m JOIN interaction_participants ip ON ip.interaction_id = m.id JOIN characters c ON c.id = ip.character_id
            GROUP BY m.id, m.story_sequence, m.interaction_type, m.summary, m.significance, m.source_excerpt, m.chapter_title ORDER BY m.story_sequence DESC
        """), params)
        return [dict(row) for row in result.mappings().all()]

    async def relationship_history(self, name_a: str, name_b: str, through_sequence: int, series_name: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        params = {"a": _key(name_a), "b": _key(name_b), "series_key": _key(series_name) if series_name else None, "through_sequence": through_sequence, "limit": limit}
        result = await self.connection.execute(text("""
            WITH people AS (
                SELECT c.id, CASE WHEN c.canonical_key = :a OR a.alias_key = :a THEN 'a' ELSE 'b' END AS which
                FROM characters c LEFT JOIN character_aliases a ON a.character_id = c.id
                WHERE (:series_key IS NULL OR c.series_key = :series_key) AND (c.canonical_key IN (:a, :b) OR a.alias_key IN (:a, :b))
            ), one AS (SELECT id FROM people WHERE which='a' LIMIT 1), two AS (SELECT id FROM people WHERE which='b' LIMIT 1)
            SELECT r.story_sequence, ch.title AS chapter_title, r.relationship_type, r.value, r.summary, r.source_excerpt
            FROM relationship_events r JOIN chapters ch ON ch.id = r.chapter_id
            WHERE r.story_sequence <= :through_sequence AND ((r.character_a_id=(SELECT id FROM one) AND r.character_b_id=(SELECT id FROM two)) OR (r.character_a_id=(SELECT id FROM two) AND r.character_b_id=(SELECT id FROM one)))
            ORDER BY r.story_sequence DESC LIMIT :limit
        """), params)
        return [dict(row) for row in result.mappings().all()]

    async def character_knowledge(self, name: str, through_sequence: int, series_name: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        params = {"name": _key(name), "series_key": _key(series_name) if series_name else None, "through_sequence": through_sequence, "limit": limit}
        result = await self.connection.execute(text("""
            WITH target AS (
                SELECT DISTINCT c.id FROM characters c LEFT JOIN character_aliases a ON a.character_id = c.id
                WHERE (:series_key IS NULL OR c.series_key = :series_key) AND (c.canonical_key = :name OR a.alias_key = :name) LIMIT 1
            ) SELECT k.story_sequence, ch.title AS chapter_title, k.fact, k.certainty, source.canonical_name AS learned_from, k.source_excerpt
            FROM knowledge_facts k JOIN target t ON t.id = k.character_id JOIN chapters ch ON ch.id = k.chapter_id LEFT JOIN characters source ON source.id = k.learned_from_character_id
            WHERE k.story_sequence <= :through_sequence ORDER BY k.story_sequence DESC LIMIT :limit
        """), params)
        return [dict(row) for row in result.mappings().all()]

    async def search_story(self, query: str, through_sequence: int, limit: int = 20) -> list[dict[str, Any]]:
        params = {"query": f"%{query}%", "through_sequence": through_sequence, "limit": limit}
        result = await self.connection.execute(text("""
            SELECT sc.story_sequence, ch.title AS chapter_title, b.title AS book_title, sc.text
            FROM story_chunks sc JOIN chapters ch ON ch.id = sc.chapter_id JOIN books b ON b.id = ch.book_id
            WHERE sc.story_sequence <= :through_sequence AND sc.text ILIKE :query ORDER BY sc.story_sequence DESC LIMIT :limit
        """), params)
        return [dict(row) for row in result.mappings().all()]
