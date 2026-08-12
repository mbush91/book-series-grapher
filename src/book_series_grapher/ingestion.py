from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ParsedChapter:
    sequence: int
    title: str
    text: str


_HEADING_RE = re.compile(
    r"(?im)^\s*(?:#{1,6}\s*)?((?:chapter\b[^\n]*|prologue\b[^\n]*|epilogue\b[^\n]*))\s*$"
)


def split_chapters(text: str) -> list[ParsedChapter]:
    """Split text/Markdown books on common chapter-like headings."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return [ParsedChapter(sequence=1, title="Chapter 1", text="")]

    matches = list(_HEADING_RE.finditer(normalized))
    if not matches:
        return [ParsedChapter(sequence=1, title="Chapter 1", text=normalized)]

    chapters: list[ParsedChapter] = []
    for idx, match in enumerate(matches):
        body_start = match.end()
        body_end = matches[idx + 1].start() if idx + 1 < len(matches) else len(normalized)
        chapters.append(
            ParsedChapter(
                sequence=idx + 1,
                title=match.group(1).strip(),
                text=normalized[body_start:body_end].strip(),
            )
        )
    return chapters
