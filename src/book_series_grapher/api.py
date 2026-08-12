from __future__ import annotations

from typing import Any

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from .settings import Settings

_SUPPORTED_EXTENSIONS = {".txt", ".md"}


class QuestionRequest(BaseModel):
    question: str = Field(min_length=1)
    through_sequence: int | None = Field(default=None, ge=0)


def _extension(filename: str) -> str:
    dot = filename.rfind(".")
    return filename[dot:].lower() if dot >= 0 else ""


def create_app(*, book_processor: Any | None = None, question_service: Any | None = None, settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()
    if book_processor is None or question_service is None:
        from .services import BookProcessor, QuestionService
        book_processor = book_processor or BookProcessor(settings)
        question_service = question_service or QuestionService(settings)

    app = FastAPI(title="Book Series Grapher API", version="0.1.0")

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/v1/books", status_code=status.HTTP_202_ACCEPTED)
    async def upload_book(file: UploadFile = File(...), title: str = Form(...), series_name: str | None = Form(default=None), series_order: int | None = Form(default=None)) -> dict[str, Any]:
        filename = file.filename or "upload"
        if _extension(filename) not in _SUPPORTED_EXTENSIONS:
            raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Only UTF-8 .txt and .md uploads are supported in the initial release.")
        content = await file.read(settings.upload_max_bytes + 1)
        if len(content) > settings.upload_max_bytes:
            raise HTTPException(status_code=413, detail="Upload exceeds UPLOAD_MAX_BYTES.")
        try:
            content.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise HTTPException(status_code=422, detail="Upload must be UTF-8 text.") from exc
        return await book_processor.submit(title=title, series_name=series_name, series_order=series_order, filename=filename, content=content)

    @app.get("/v1/books/{book_id}")
    async def book_status(book_id: str) -> dict[str, Any]:
        result = await book_processor.status(book_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Book not found")
        return result

    @app.post("/v1/questions")
    async def ask_question(request: QuestionRequest) -> dict[str, Any]:
        return await question_service.ask(request.question, request.through_sequence)

    return app
