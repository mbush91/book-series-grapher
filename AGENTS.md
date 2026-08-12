# AGENTS.md

## Project goal
Build a spoiler-safe book-series knowledge system that ingests books chapter-by-chapter, extracts characters, aliases, scenes, interactions, temporal state, relationships, and character-specific knowledge, then answers questions as of a requested story position.

## Architecture rules
- PostgreSQL + pgvector is the source of truth.
- Preserve history: never overwrite story facts when a temporal record is appropriate.
- Every extracted fact must be traceable to a book/chapter and source text span when available.
- Character interactions are first-class entities with participants, roles, and outcomes.
- FastMCP owns deterministic domain/query tools and their instructions/descriptions.
- FastAPI owns HTTP upload/question endpoints and uses Pydantic AI as the model orchestration layer.
- The API talks to the MCP service over Streamable HTTP; do not duplicate DB query logic in the API agent.
- Model provider/name/API keys and reasoning/thinking effort come from environment variables.
- Docker Compose is the default local/runtime entry point.

## TDD rules
1. Add or change a failing test first (RED).
2. Implement the smallest behavior that makes it pass (GREEN).
3. Refactor while keeping tests green.
4. Keep tests deterministic; model calls must be replaceable/fakeable in unit tests.
5. Database integration tests should run against PostgreSQL, not SQLite, for PostgreSQL-specific behavior.

## Current progress
- [x] Architecture direction established.
- [x] RED: domain, parser, settings, API, and spoiler-cutoff tests added before implementation.
- [ ] GREEN: implementation.
- [ ] Docker Compose wiring.
- [ ] Documentation and example environment.

## Initial scope
- Accept UTF-8 `.txt` and `.md` book uploads.
- Persist books/chapters and extracted structured story facts.
- Expose MCP tools for story-position-aware character status, interaction timelines, relationship/knowledge lookup, and text search.
- Provide FastAPI endpoints for health, upload/process, processing status, and questions.
- Keep file-format parsing extensible for EPUB/PDF later.

## Test contracts now driving implementation
- Interactions must have at least two participants.
- Extraction references must resolve to characters declared in the same chapter analysis.
- Chapter parsing recognizes Markdown/plain Chapter, Prologue, and Epilogue headings.
- Model effort is represented with Pydantic AI's provider-portable `thinking` setting.
- Upload endpoints accept only the currently supported text formats.
- Every temporal character lookup takes an explicit `through_sequence` cutoff.
