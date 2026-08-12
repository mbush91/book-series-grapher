from __future__ import annotations

import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from .settings import Settings


class Base(DeclarativeBase):
    pass


class Book(Base):
    __tablename__ = "books"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    series_name: Mapped[str | None] = mapped_column(String(500))
    series_key: Mapped[str] = mapped_column(String(500), index=True)
    series_order: Mapped[int | None] = mapped_column(Integer)
    source_filename: Mapped[str | None] = mapped_column(String(1000))
    status: Mapped[str] = mapped_column(String(50), default="queued", index=True)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Chapter(Base):
    __tablename__ = "chapters"
    __table_args__ = (UniqueConstraint("book_id", "chapter_sequence"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    book_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("books.id", ondelete="CASCADE"), index=True)
    chapter_sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    story_sequence: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text)


class Character(Base):
    __tablename__ = "characters"
    __table_args__ = (UniqueConstraint("series_key", "canonical_key"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    series_key: Mapped[str] = mapped_column(String(500), index=True)
    canonical_name: Mapped[str] = mapped_column(String(500), nullable=False)
    canonical_key: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)


class CharacterAlias(Base):
    __tablename__ = "character_aliases"
    __table_args__ = (UniqueConstraint("series_key", "alias_key"),)
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    character_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("characters.id", ondelete="CASCADE"), index=True)
    series_key: Mapped[str] = mapped_column(String(500), index=True)
    alias: Mapped[str] = mapped_column(String(500), nullable=False)
    alias_key: Mapped[str] = mapped_column(String(500), nullable=False)


class CharacterEvent(Base):
    __tablename__ = "character_events"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chapter_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("chapters.id", ondelete="CASCADE"), index=True)
    character_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("characters.id", ondelete="CASCADE"), index=True)
    story_sequence: Mapped[int] = mapped_column(BigInteger, index=True)
    event_type: Mapped[str] = mapped_column(String(200))
    summary: Mapped[str] = mapped_column(Text)
    source_excerpt: Mapped[str | None] = mapped_column(Text)


class CharacterState(Base):
    __tablename__ = "character_states"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chapter_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("chapters.id", ondelete="CASCADE"), index=True)
    character_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("characters.id", ondelete="CASCADE"), index=True)
    story_sequence: Mapped[int] = mapped_column(BigInteger, index=True)
    attribute: Mapped[str] = mapped_column(String(200), index=True)
    value: Mapped[object] = mapped_column(JSONB)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    source_excerpt: Mapped[str | None] = mapped_column(Text)


class Interaction(Base):
    __tablename__ = "interactions"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chapter_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("chapters.id", ondelete="CASCADE"), index=True)
    story_sequence: Mapped[int] = mapped_column(BigInteger, index=True)
    interaction_type: Mapped[str] = mapped_column(String(200), index=True)
    summary: Mapped[str] = mapped_column(Text)
    significance: Mapped[str | None] = mapped_column(Text)
    source_excerpt: Mapped[str | None] = mapped_column(Text)


class InteractionParticipant(Base):
    __tablename__ = "interaction_participants"
    interaction_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("interactions.id", ondelete="CASCADE"), primary_key=True)
    character_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("characters.id", ondelete="CASCADE"), primary_key=True)
    role: Mapped[str | None] = mapped_column(String(200))
    disposition: Mapped[str | None] = mapped_column(String(200))


class RelationshipEvent(Base):
    __tablename__ = "relationship_events"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chapter_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("chapters.id", ondelete="CASCADE"), index=True)
    character_a_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("characters.id", ondelete="CASCADE"), index=True)
    character_b_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("characters.id", ondelete="CASCADE"), index=True)
    story_sequence: Mapped[int] = mapped_column(BigInteger, index=True)
    relationship_type: Mapped[str] = mapped_column(String(200), index=True)
    value: Mapped[str | None] = mapped_column(String(500))
    summary: Mapped[str] = mapped_column(Text)
    source_excerpt: Mapped[str | None] = mapped_column(Text)


class KnowledgeFact(Base):
    __tablename__ = "knowledge_facts"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chapter_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("chapters.id", ondelete="CASCADE"), index=True)
    character_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("characters.id", ondelete="CASCADE"), index=True)
    learned_from_character_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("characters.id", ondelete="SET NULL"))
    story_sequence: Mapped[int] = mapped_column(BigInteger, index=True)
    fact: Mapped[str] = mapped_column(Text)
    certainty: Mapped[float] = mapped_column(Float, default=1.0)
    source_excerpt: Mapped[str | None] = mapped_column(Text)


class StoryChunk(Base):
    __tablename__ = "story_chunks"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chapter_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("chapters.id", ondelete="CASCADE"), index=True)
    story_sequence: Mapped[int] = mapped_column(BigInteger, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[object | None] = mapped_column(Vector(), nullable=True)


def make_engine(settings: Settings | None = None) -> AsyncEngine:
    settings = settings or Settings()
    return create_async_engine(settings.database_url, pool_pre_ping=True)


async def init_db(engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        await connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await connection.run_sync(Base.metadata.create_all)
