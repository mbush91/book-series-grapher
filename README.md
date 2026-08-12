# Book Series Grapher

A temporal, spoiler-safe knowledge system for very long book series. It tracks characters, aliases, chapter-by-chapter state, interactions, relationship changes, and what each character personally knows.

## Architecture

- **PostgreSQL + pgvector** is the source of truth. Story history is append-oriented and every query can be bounded by a story sequence.
- **FastMCP service** exposes deterministic write/read tools plus instructions that tell agents how to use the temporal model safely.
- **FastAPI service** exposes upload/status/question HTTP endpoints.
- **Pydantic AI** runs chapter extraction and question-answering agents and consumes the MCP server as a toolset.
- **Docker Compose** runs PostgreSQL, MCP, and API as separate containers.

The first slice stores raw chapter text in `story_chunks` with a nullable pgvector column. Lexical search is implemented now; embeddings can be populated later without changing the primary data model.

## Run

```bash
cp .env.example .env
# Fill in the API key for the provider in MODEL_NAME.
docker compose up --build
```

API docs: `http://localhost:8000/docs`
MCP endpoint: `http://localhost:8001/mcp`

## Upload a book

Initial parsing supports UTF-8 `.txt` and `.md` files with headings such as `Chapter 1`, `# Chapter One`, `Prologue`, and `Epilogue`.

```bash
curl -X POST http://localhost:8000/v1/books \
  -F 'title=Example Book' \
  -F 'series_name=Example Series' \
  -F 'series_order=1' \
  -F 'file=@book.md'
```

The response returns a `book_id`. Poll `GET /v1/books/{book_id}` for `queued`, `processing`, `completed`, or `failed`.

## Ask a spoiler-bounded question

```bash
curl -X POST http://localhost:8000/v1/questions \
  -H 'content-type: application/json' \
  -d '{"question":"What is Alice's relationship with Bob?","through_sequence":1000042}'
```

Story sequence is currently computed as `series_order * 1,000,000 + chapter_sequence`, so book 1 chapter 42 is `1000042`. A later API can resolve human-friendly book/chapter positions to this internal sequence.

## What is tracked

- canonical characters and aliases
- character events
- temporal state changes (location, health, allegiance, goals, possessions, etc.)
- first-class interactions with all participants, roles, dispositions, and outcomes/summaries
- relationship changes between character pairs
- character-specific knowledge with source character and certainty
- chapter source text and concise evidence excerpts

Every reader-facing MCP lookup takes `through_sequence` and applies it in SQL so future chapters cannot leak into the agent context.

## Model configuration

`MODEL_NAME` uses Pydantic AI provider/model syntax. `MODEL_EFFORT` is passed through Pydantic AI's provider-portable `thinking` setting. Optional `EXTRACTION_MODEL_NAME` and `EXTRACTION_MODEL_EFFORT` let ingestion use a different model from Q&A. Provider API keys are read from standard environment variables such as `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, and `GOOGLE_API_KEY`.

## Development / TDD

```bash
python -m venv .venv
. .venv/bin/activate
pip install -e '.[dev]'
pytest
```

See `AGENTS.md` for architecture rules and the required RED → GREEN → refactor workflow.
