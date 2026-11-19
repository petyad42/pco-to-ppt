"""Planning Center Online fetch layer.

The pure parsing functions (``parse_songs_from_items``, ``parse_arrangement`` and
friends) take already-decoded JSON and return plain data, so they can be tested
with recorded fixtures and no network. The ``fetch_*`` functions wrap them with
``requests`` calls and are the only part that touches the network.

Lifted from the original ``jsonparser.py``; the Ableton .als handling is dropped.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import requests

from .models import Section, Song

API_BASE = "https://api.planningcenteronline.com/services/v2"


# --------------------------------------------------------------------------- #
# Input parsing
# --------------------------------------------------------------------------- #

def parse_plan_id(url_or_id: str) -> str:
    """Extract a plan ID from a full PCO service URL or a bare ID.

    Accepts e.g. ``https://services.planningcenteronline.com/plans/91675400``
    or just ``91675400``. Raises ``ValueError`` on anything else.
    """
    value = (url_or_id or "").strip()
    if not value:
        raise ValueError("empty plan identifier")

    if value.isdigit():
        return value

    parsed = urlparse(value)
    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"invalid plan URL or ID: {url_or_id!r}")

    tail = parsed.path.rstrip("/").split("/")[-1]
    if not tail.isdigit():
        raise ValueError(f"could not find a plan ID in URL: {url_or_id!r}")
    return tail


# --------------------------------------------------------------------------- #
# Pure JSON parsing (fixture-testable, no network)
# --------------------------------------------------------------------------- #

def parse_songs_from_items(items_json: Dict[str, Any]) -> List[Song]:
    """Parse a single ``/plans/{id}/items`` page into songs, preserving order.

    Only items with ``item_type == "song"`` are kept; everything else (headers,
    media, announcements) is ignored.
    """
    songs: List[Song] = []
    for item in items_json.get("data", []):
        attrs = item.get("attributes", {})
        if attrs.get("item_type") != "song":
            continue
        relationships = item.get("relationships", {})
        song_data = relationships.get("song", {}).get("data")
        arr_data = relationships.get("arrangement", {}).get("data")
        songs.append(
            Song(
                title=attrs.get("title") or "",
                key_name=attrs.get("key_name"),
                song_id=song_data.get("id") if song_data else None,
                arrangement_id=arr_data.get("id") if arr_data else None,
            )
        )
    return songs


def next_link(page_json: Dict[str, Any]) -> Optional[str]:
    """Return the pagination ``links.next`` URL, or ``None`` when exhausted."""
    return page_json.get("links", {}).get("next")


def parse_arrangement(arrangement_json: Dict[str, Any]) -> Dict[str, Any]:
    """Pull bpm/meter from an arrangement response."""
    attrs = arrangement_json.get("data", {}).get("attributes", {})
    return {"bpm": attrs.get("bpm"), "meter": attrs.get("meter")}


def parse_sections(sections_json: Dict[str, Any]) -> List[Section]:
    """Parse an ``arrangement_sections`` response into Section objects.

    PCO returns the structured blocks under ``data.attributes.sections`` as a
    list of ``{"label", "lyrics", "breaks_at"}``. Sections without lyrics text
    are skipped. Returns an empty list when no structured sections exist, which
    is the caller's signal to fall back to the raw lyrics field.
    """
    attrs = sections_json.get("data", {}).get("attributes", {})
    raw_sections = attrs.get("sections") or []
    result: List[Section] = []
    for block in raw_sections:
        lyrics = block.get("lyrics")
        if not lyrics or not lyrics.strip():
            continue
        result.append(Section(label=block.get("label"), lyrics=lyrics))
    return result


def sections_from_arrangement_lyrics(arrangement_json: Dict[str, Any]) -> List[Section]:
    """Fallback: build a single unlabelled Section from an arrangement's raw lyrics."""
    attrs = arrangement_json.get("data", {}).get("attributes", {})
    lyrics = attrs.get("lyrics")
    if lyrics and lyrics.strip():
        return [Section(label=None, lyrics=lyrics)]
    return []


# --------------------------------------------------------------------------- #
# Network layer
# --------------------------------------------------------------------------- #

def _headers(token: str) -> Dict[str, str]:
    return {"Authorization": token}


def get_token() -> str:
    """Read the PCO token from the environment (loaded from .env by the CLI)."""
    token = os.getenv("PCO_TOKEN")
    if not token:
        raise RuntimeError(
            "PCO_TOKEN is not set. Put it in a .env file as PCO_TOKEN=<your token>."
        )
    return token


def fetch_plan_songs(plan_id: str, token: str, session: Optional[requests.Session] = None) -> List[Song]:
    """Fetch and page through all song items in a plan, preserving order."""
    sess = session or requests.Session()
    url = f"{API_BASE}/plans/{plan_id}/items"
    songs: List[Song] = []
    while url:
        resp = sess.get(url, headers=_headers(token))
        resp.raise_for_status()
        page = resp.json()
        songs.extend(parse_songs_from_items(page))
        url = next_link(page)
    return songs


def enrich_song(song: Song, token: str, session: Optional[requests.Session] = None) -> Song:
    """Fill in bpm/meter and sections for one song via the arrangement endpoints.

    Prefers structured arrangement sections; falls back to the arrangement's raw
    lyrics field when no structured sections are present.
    """
    if not (song.song_id and song.arrangement_id):
        return song
    sess = session or requests.Session()
    arr_url = f"{API_BASE}/songs/{song.song_id}/arrangements/{song.arrangement_id}"

    arr_resp = sess.get(arr_url, headers=_headers(token))
    arr_resp.raise_for_status()
    arr_json = arr_resp.json()
    meta = parse_arrangement(arr_json)
    song.bpm = meta["bpm"]
    song.meter = meta["meter"]

    sec_resp = sess.get(f"{arr_url}/sections", headers=_headers(token))
    sec_resp.raise_for_status()
    sections = parse_sections(sec_resp.json())
    if not sections:
        sections = sections_from_arrangement_lyrics(arr_json)
    song.sections = sections
    return song
