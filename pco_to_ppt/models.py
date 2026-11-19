"""Plain data structures shared across the library.

These carry data between the fetch, chunking, and deck layers. Keeping them free
of any I/O or API detail is what lets a future web app reuse the core.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class Section:
    """A labelled block of lyrics from a song arrangement.

    ``label`` is kept for display/debugging only -- it is deliberately NOT
    rendered onto slides (slides show pure lyrics). ``lyrics`` preserves the
    text exactly as PCO returned it, including accented characters: it must
    never be transliterated.
    """

    label: Optional[str]
    lyrics: str


@dataclass
class Song:
    """A song item from a plan, enriched with arrangement data and sections."""

    title: str
    key_name: Optional[str] = None
    bpm: Optional[int] = None
    meter: Optional[str] = None
    song_id: Optional[str] = None
    arrangement_id: Optional[str] = None
    sections: List[Section] = field(default_factory=list)
