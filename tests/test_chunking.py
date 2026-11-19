"""Tests for the pure lyric-to-slide chunking logic (primary seam)."""

from pco_to_ppt.chunking import DEFAULT_MAX_LINES, chunk_lyrics, chunk_sections
from pco_to_ppt.models import Section


def test_short_section_stays_on_one_slide():
    lyrics = "line one\nline two\nline three"
    assert chunk_lyrics(lyrics, max_lines=4) == ["line one\nline two\nline three"]


def test_section_at_exactly_max_is_not_split():
    lyrics = "a\nb\nc\nd"
    assert chunk_lyrics(lyrics, max_lines=4) == ["a\nb\nc\nd"]


def test_section_over_max_is_split():
    lyrics = "\n".join(f"l{i}" for i in range(1, 6))  # 5 lines, max 4
    slides = chunk_lyrics(lyrics, max_lines=4)
    assert len(slides) == 2


def test_split_only_on_line_boundaries():
    lines = [f"line number {i}" for i in range(1, 8)]
    slides = chunk_lyrics("\n".join(lines), max_lines=3)
    # Re-joining every slide's lines must reproduce the original lines in order,
    # with no line ever cut in half.
    recombined = []
    for slide in slides:
        recombined.extend(slide.split("\n"))
    assert recombined == lines


def test_nine_lines_at_max_four_is_balanced_not_greedy():
    lyrics = "\n".join(f"l{i}" for i in range(1, 10))  # 9 lines
    slides = chunk_lyrics(lyrics, max_lines=4)
    sizes = [len(s.split("\n")) for s in slides]
    # Minimum slides that respect max=4 is ceil(9/4)=3, then balanced evenly
    # -> 3+3+3. Never greedy 4+4+1, and never a 5-line slide (which would break
    # the max). No slide exceeds the max; sizes differ by at most one.
    assert sizes == [3, 3, 3]
    assert max(sizes) <= 4
    assert max(sizes) - min(sizes) <= 1


def test_nine_lines_at_max_three_is_three_even_chunks():
    lyrics = "\n".join(f"l{i}" for i in range(1, 10))  # 9 lines
    slides = chunk_lyrics(lyrics, max_lines=3)
    sizes = [len(s.split("\n")) for s in slides]
    assert sizes == [3, 3, 3]


def test_remainder_goes_to_earliest_slides():
    lyrics = "\n".join(f"l{i}" for i in range(1, 11))  # 10 lines, max 4 -> 3 slides
    slides = chunk_lyrics(lyrics, max_lines=4)
    sizes = [len(s.split("\n")) for s in slides]
    assert sizes == [4, 3, 3]
    assert sum(sizes) == 10


def test_no_labels_appear_in_output():
    section = Section(label="Chorus", lyrics="sing\nout\nloud")
    slides = chunk_sections([section], max_lines=4)
    joined = "\n".join(slides)
    assert "Chorus" not in joined


def test_accented_characters_preserved():
    lyrics = "Rejts most el a szárnyad alá,\nErős kézzel takarj be engem."
    slides = chunk_lyrics(lyrics, max_lines=4)
    assert "szárnyad" in slides[0]
    assert "Erős" in slides[0]


def test_configurable_max_other_than_default():
    assert DEFAULT_MAX_LINES == 4
    lyrics = "\n".join(f"l{i}" for i in range(1, 5))  # 4 lines
    # With max 2, the 4-line section must split into two slides of 2.
    slides = chunk_lyrics(lyrics, max_lines=2)
    assert [len(s.split("\n")) for s in slides] == [2, 2]


def test_blank_lines_are_ignored():
    lyrics = "a\n\n\nb"
    assert chunk_lyrics(lyrics, max_lines=4) == ["a\nb"]


def test_empty_section_yields_no_slides():
    assert chunk_lyrics("   \n  \n", max_lines=4) == []


def test_sections_are_not_merged_onto_one_slide():
    sections = [Section(None, "a\nb"), Section(None, "c\nd")]
    slides = chunk_sections(sections, max_lines=4)
    # Two short sections -> two separate slides, never combined.
    assert slides == ["a\nb", "c\nd"]


def test_punctuation_only_section_yields_no_slides():
    # PCO arrangements use sections like ". ." as intro/instrumental markers.
    assert chunk_lyrics(". .", max_lines=4) == []
    assert chunk_lyrics("..\n...\n- -", max_lines=4) == []


def test_punctuation_only_lines_dropped_but_lyrics_kept():
    assert chunk_lyrics(". .\nTe vagy az Úr!\n..", max_lines=4) == ["Te vagy az Úr!"]


def test_lines_with_punctuation_and_words_are_kept():
    assert chunk_lyrics("(Vége: )\nHalleluja!", max_lines=4) == ["(Vége: )\nHalleluja!"]
