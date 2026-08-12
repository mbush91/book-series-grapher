import pytest
from pydantic import ValidationError

from book_series_grapher.domain import (
    ChapterAnalysis,
    CharacterExtract,
    InteractionExtract,
    InteractionParticipantExtract,
)


def test_interaction_requires_at_least_two_participants() -> None:
    with pytest.raises(ValidationError):
        InteractionExtract(
            interaction_type="conversation",
            summary="A private conversation.",
            participants=[InteractionParticipantExtract(character_ref="alice")],
        )


def test_chapter_analysis_rejects_unknown_character_references() -> None:
    with pytest.raises(ValidationError, match="unknown character ref"):
        ChapterAnalysis(
            summary="Alice speaks to an unnamed person.",
            characters=[CharacterExtract(ref="alice", canonical_name="Alice")],
            interactions=[
                InteractionExtract(
                    interaction_type="conversation",
                    summary="Alice and Bob speak.",
                    participants=[
                        InteractionParticipantExtract(character_ref="alice"),
                        InteractionParticipantExtract(character_ref="bob"),
                    ],
                )
            ],
        )
