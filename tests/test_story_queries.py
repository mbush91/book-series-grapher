import pytest

from book_series_grapher.repository import StoryRepository


class RecordingConnection:
    def __init__(self) -> None:
        self.params = None

    async def execute(self, statement, params):
        self.params = params

        class Result:
            def mappings(self):
                return self
            def all(self):
                return []

        return Result()


@pytest.mark.asyncio
async def test_character_timeline_always_applies_story_sequence_cutoff() -> None:
    connection = RecordingConnection()
    repo = StoryRepository(connection)  # type: ignore[arg-type]

    await repo.character_timeline("Alice", through_sequence=120)

    assert connection.params["through_sequence"] == 120
