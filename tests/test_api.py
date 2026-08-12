from fastapi.testclient import TestClient

from book_series_grapher.api import create_app


class FakeBookProcessor:
    async def submit(self, *, title: str, series_name: str | None, series_order: int | None, filename: str, content: bytes):
        assert title == "Test Book"
        assert filename == "test.md"
        assert b"Chapter 1" in content
        return {"book_id": "book-1", "status": "queued", "chapter_count": 1}


class FakeQuestionService:
    async def ask(self, question: str, through_sequence: int | None):
        return {"answer": "Alice is alive.", "through_sequence": through_sequence}


def test_upload_accepts_markdown_book() -> None:
    app = create_app(book_processor=FakeBookProcessor(), question_service=FakeQuestionService())
    client = TestClient(app)

    response = client.post(
        "/v1/books",
        data={"title": "Test Book"},
        files={"file": ("test.md", b"# Chapter 1\nAlice arrived.", "text/markdown")},
    )

    assert response.status_code == 202
    assert response.json()["status"] == "queued"


def test_upload_rejects_unsupported_extension() -> None:
    app = create_app(book_processor=FakeBookProcessor(), question_service=FakeQuestionService())
    client = TestClient(app)

    response = client.post(
        "/v1/books",
        data={"title": "Test Book"},
        files={"file": ("test.pdf", b"not a pdf", "application/pdf")},
    )

    assert response.status_code == 415


def test_question_passes_spoiler_cutoff_to_service() -> None:
    app = create_app(book_processor=FakeBookProcessor(), question_service=FakeQuestionService())
    client = TestClient(app)

    response = client.post("/v1/questions", json={"question": "Where is Alice?", "through_sequence": 42})

    assert response.status_code == 200
    assert response.json() == {"answer": "Alice is alive.", "through_sequence": 42}
