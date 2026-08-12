from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, model_validator


class CharacterExtract(BaseModel):
    ref: str = Field(min_length=1, description="Chapter-local stable reference used by other extracted objects.")
    canonical_name: str = Field(min_length=1)
    aliases: list[str] = Field(default_factory=list)
    description: str | None = None


class InteractionParticipantExtract(BaseModel):
    character_ref: str = Field(min_length=1)
    role: str | None = None
    disposition: str | None = None


class InteractionExtract(BaseModel):
    interaction_type: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    participants: list[InteractionParticipantExtract] = Field(min_length=2)
    significance: str | None = None
    source_excerpt: str | None = None

    @model_validator(mode="after")
    def participants_are_distinct(self) -> "InteractionExtract":
        refs = [p.character_ref for p in self.participants]
        if len(set(refs)) < 2:
            raise ValueError("interaction requires at least two distinct participants")
        return self


class CharacterEventExtract(BaseModel):
    character_ref: str = Field(min_length=1)
    event_type: str = Field(min_length=1)
    summary: str = Field(min_length=1)
    source_excerpt: str | None = None


class CharacterStateExtract(BaseModel):
    character_ref: str = Field(min_length=1)
    attribute: str = Field(min_length=1, description="Examples: location, health, allegiance, goal, possession.")
    value: Any
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    source_excerpt: str | None = None


class RelationshipChangeExtract(BaseModel):
    character_a_ref: str = Field(min_length=1)
    character_b_ref: str = Field(min_length=1)
    relationship_type: str = Field(min_length=1)
    value: str | None = None
    summary: str = Field(min_length=1)
    source_excerpt: str | None = None


class KnowledgeExtract(BaseModel):
    character_ref: str = Field(min_length=1, description="The character who knows or believes the fact.")
    fact: str = Field(min_length=1)
    learned_from_character_ref: str | None = None
    certainty: float = Field(default=1.0, ge=0.0, le=1.0)
    source_excerpt: str | None = None


class ChapterAnalysis(BaseModel):
    summary: str = Field(min_length=1)
    characters: list[CharacterExtract] = Field(default_factory=list)
    events: list[CharacterEventExtract] = Field(default_factory=list)
    states: list[CharacterStateExtract] = Field(default_factory=list)
    interactions: list[InteractionExtract] = Field(default_factory=list)
    relationships: list[RelationshipChangeExtract] = Field(default_factory=list)
    knowledge: list[KnowledgeExtract] = Field(default_factory=list)

    @model_validator(mode="after")
    def references_resolve(self) -> "ChapterAnalysis":
        refs = {character.ref for character in self.characters}
        all_refs: list[str] = []
        all_refs.extend(event.character_ref for event in self.events)
        all_refs.extend(state.character_ref for state in self.states)
        for interaction in self.interactions:
            all_refs.extend(participant.character_ref for participant in interaction.participants)
        for relation in self.relationships:
            all_refs.extend([relation.character_a_ref, relation.character_b_ref])
        for fact in self.knowledge:
            all_refs.append(fact.character_ref)
            if fact.learned_from_character_ref:
                all_refs.append(fact.learned_from_character_ref)
        unknown = sorted(set(all_refs) - refs)
        if unknown:
            raise ValueError(f"unknown character ref(s): {', '.join(unknown)}")
        return self
