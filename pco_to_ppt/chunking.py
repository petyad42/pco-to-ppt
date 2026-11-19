"""Pure lyric-to-slide chunking logic (no I/O).

This is the primary test seam. Given a section's lyrics and a maximum number of
lines per slide, it returns the ordered slide text blocks. Rules:

- A section maps to one or more slides.
- Split only when the section exceeds the max line count.
- Break on line boundaries only -- never mid-line.
- Balance chunks evenly rather than greedy-packing
  (9 lines at max 4 -> 5+4 or 3+3+3, never 4+4+1).
- No labels are emitted; output is lyric text only.
- Text is preserved exactly (accents and all); nothing is transliterated here.
"""

from __future__ import annotations

import math
from typing import List

from .models import Section

DEFAULT_MAX_LINES = 4


def _has_words(line: str) -> bool:
    """True if the line contains at least one letter or digit (Unicode-aware)."""
    return any(ch.isalnum() for ch in line)


def _split_lines(lyrics: str) -> List[str]:
    """Split a lyrics block into lyric lines, preserving characters exactly.

    Dropped lines:
    - blank lines (spacing in PCO), so they don't use up the per-slide budget;
    - punctuation-only lines such as ". ." which PCO arrangements use as
      placeholder sections (intro/instrumental markers). They would otherwise
      become slides showing only dots.
    """
    return [line.strip() for line in lyrics.splitlines() if _has_words(line)]


def _balanced_chunk_sizes(total: int, max_lines: int) -> List[int]:
    """Return chunk sizes that split ``total`` lines into evenly balanced slides.

    The number of slides is the minimum needed so no slide exceeds ``max_lines``
    (ceil division). Lines are then spread as evenly as possible across those
    slides, with any remainder distributed to the earliest slides. This avoids a
    near-empty trailing slide: 9 lines at max 4 -> [5, 4], not [4, 4, 1].
    """
    if total <= 0:
        return []
    num_slides = math.ceil(total / max_lines)
    base = total // num_slides
    remainder = total % num_slides
    # The first ``remainder`` slides get one extra line.
    return [base + 1 if i < remainder else base for i in range(num_slides)]


def chunk_lyrics(lyrics: str, max_lines: int = DEFAULT_MAX_LINES) -> List[str]:
    """Split one lyrics block into a list of slide texts (joined by newlines)."""
    if max_lines < 1:
        raise ValueError("max_lines must be at least 1")

    lines = _split_lines(lyrics)
    if not lines:
        return []

    if len(lines) <= max_lines:
        return ["\n".join(lines)]

    sizes = _balanced_chunk_sizes(len(lines), max_lines)
    slides: List[str] = []
    cursor = 0
    for size in sizes:
        slides.append("\n".join(lines[cursor:cursor + size]))
        cursor += size
    return slides


def chunk_section(section: Section, max_lines: int = DEFAULT_MAX_LINES) -> List[str]:
    """Chunk a single section into slide texts."""
    return chunk_lyrics(section.lyrics, max_lines=max_lines)


def chunk_sections(sections: List[Section], max_lines: int = DEFAULT_MAX_LINES) -> List[str]:
    """Chunk all sections of a song, in order, into a flat list of slide texts.

    Each section starts fresh on a new slide; sections are never merged onto one
    slide, so song structure is preserved.
    """
    slides: List[str] = []
    for section in sections:
        slides.extend(chunk_section(section, max_lines=max_lines))
    return slides
