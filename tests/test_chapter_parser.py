from book_series_grapher.ingestion import split_chapters


def test_split_chapters_recognizes_markdown_and_plain_headings() -> None:
    text = """# Chapter One\nAlice arrived.\n\nCHAPTER 2\nBob left.\n\n## Epilogue\nYears passed.\n"""

    chapters = split_chapters(text)

    assert [chapter.title for chapter in chapters] == ["Chapter One", "CHAPTER 2", "Epilogue"]
    assert [chapter.sequence for chapter in chapters] == [1, 2, 3]
    assert chapters[0].text == "Alice arrived."


def test_split_chapters_treats_unheaded_text_as_one_chapter() -> None:
    chapters = split_chapters("A short story with no explicit headings.")

    assert len(chapters) == 1
    assert chapters[0].title == "Chapter 1"
    assert chapters[0].sequence == 1
