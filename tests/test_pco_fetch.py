"""Tests for the PCO fetch parsing layer (boundary seam), using JSON fixtures.

These exercise the pure parsing + pagination logic with recorded-shape JSON and
a fake session -- no real network and no token required.
"""

import pytest

from pco_to_ppt import pco_fetch
from pco_to_ppt.pco_fetch import (
    next_link,
    parse_arrangement,
    parse_plan_id,
    parse_sections,
    parse_songs_from_items,
    sections_from_arrangement_lyrics,
)


# --------------------------------------------------------------------------- #
# parse_plan_id
# --------------------------------------------------------------------------- #

def test_parse_plan_id_from_full_url():
    url = "https://services.planningcenteronline.com/plans/91675400"
    assert parse_plan_id(url) == "91675400"


def test_parse_plan_id_from_bare_id():
    assert parse_plan_id("91675400") == "91675400"


def test_parse_plan_id_strips_trailing_slash():
    assert parse_plan_id("https://services.planningcenteronline.com/plans/123/") == "123"


def test_parse_plan_id_rejects_garbage():
    with pytest.raises(ValueError):
        parse_plan_id("not a url or id")


def test_parse_plan_id_rejects_empty():
    with pytest.raises(ValueError):
        parse_plan_id("")


# --------------------------------------------------------------------------- #
# parse_songs_from_items
# --------------------------------------------------------------------------- #

def _item(item_type, title, song_id="s1", arr_id="a1"):
    return {
        "attributes": {"item_type": item_type, "title": title, "key_name": "G"},
        "relationships": {
            "song": {"data": {"id": song_id}},
            "arrangement": {"data": {"id": arr_id}},
        },
    }


def test_filters_to_songs_only():
    items = {
        "data": [
            _item("header", "Welcome"),
            _item("song", "Song A"),
            _item("media", "Video"),
            _item("song", "Song B"),
        ]
    }
    songs = parse_songs_from_items(items)
    assert [s.title for s in songs] == ["Song A", "Song B"]


def test_preserves_plan_order():
    items = {"data": [_item("song", "First"), _item("song", "Second"), _item("song", "Third")]}
    songs = parse_songs_from_items(items)
    assert [s.title for s in songs] == ["First", "Second", "Third"]


def test_captures_song_and_arrangement_ids():
    items = {"data": [_item("song", "A", song_id="99", arr_id="77")]}
    song = parse_songs_from_items(items)[0]
    assert song.song_id == "99"
    assert song.arrangement_id == "77"


def test_handles_missing_relationships():
    items = {"data": [{"attributes": {"item_type": "song", "title": "Lonely"}}]}
    song = parse_songs_from_items(items)[0]
    assert song.title == "Lonely"
    assert song.song_id is None
    assert song.arrangement_id is None


# --------------------------------------------------------------------------- #
# pagination
# --------------------------------------------------------------------------- #

def test_next_link_present_and_absent():
    assert next_link({"links": {"next": "http://x/page2"}}) == "http://x/page2"
    assert next_link({"links": {}}) is None
    assert next_link({}) is None


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


class _FakeSession:
    """Returns queued pages in order, ignoring the requested URL."""

    def __init__(self, pages):
        self._pages = list(pages)

    def get(self, url, headers=None):
        return _FakeResponse(self._pages.pop(0))


def test_fetch_plan_songs_follows_pagination():
    page1 = {
        "data": [_item("song", "A"), _item("header", "H")],
        "links": {"next": "http://api/page2"},
    }
    page2 = {"data": [_item("song", "B")], "links": {}}
    session = _FakeSession([page1, page2])
    songs = pco_fetch.fetch_plan_songs("123", token="t", session=session)
    assert [s.title for s in songs] == ["A", "B"]


# --------------------------------------------------------------------------- #
# arrangement + sections parsing
# --------------------------------------------------------------------------- #

def test_parse_arrangement_bpm_meter():
    arr = {"data": {"attributes": {"bpm": 72, "meter": "4/4"}}}
    assert parse_arrangement(arr) == {"bpm": 72, "meter": "4/4"}


def test_parse_sections_structured():
    payload = {
        "data": {
            "attributes": {
                "sections": [
                    {"label": "Verse", "lyrics": "be thou my vision", "breaks_at": None},
                    {"label": "Chorus", "lyrics": "high king of heaven", "breaks_at": None},
                ]
            }
        }
    }
    sections = parse_sections(payload)
    assert [s.label for s in sections] == ["Verse", "Chorus"]
    assert sections[0].lyrics == "be thou my vision"


def test_parse_sections_skips_empty_lyrics():
    payload = {"data": {"attributes": {"sections": [{"label": "Verse", "lyrics": "  "}]}}}
    assert parse_sections(payload) == []


def test_parse_sections_empty_when_none():
    assert parse_sections({"data": {"attributes": {}}}) == []


def test_fallback_to_raw_lyrics_when_no_sections():
    arr = {"data": {"attributes": {"lyrics": "just the words\nsecond line"}}}
    fallback = sections_from_arrangement_lyrics(arr)
    assert len(fallback) == 1
    assert fallback[0].label is None
    assert "second line" in fallback[0].lyrics


def test_enrich_song_prefers_sections_over_fallback():
    arr_json = {"data": {"attributes": {"bpm": 80, "meter": "6/8", "lyrics": "raw fallback"}}}
    sections_json = {
        "data": {"attributes": {"sections": [{"label": "Verse", "lyrics": "structured"}]}}
    }
    from pco_to_ppt.models import Song

    song = Song(title="X", song_id="1", arrangement_id="2")
    session = _FakeSession([arr_json, sections_json])
    pco_fetch.enrich_song(song, token="t", session=session)
    assert song.bpm == 80
    assert song.meter == "6/8"
    assert [s.lyrics for s in song.sections] == ["structured"]


def test_enrich_song_falls_back_when_no_structured_sections():
    arr_json = {"data": {"attributes": {"bpm": None, "meter": None, "lyrics": "fallback words"}}}
    sections_json = {"data": {"attributes": {"sections": []}}}
    from pco_to_ppt.models import Song

    song = Song(title="X", song_id="1", arrangement_id="2")
    session = _FakeSession([arr_json, sections_json])
    pco_fetch.enrich_song(song, token="t", session=session)
    assert [s.lyrics for s in song.sections] == ["fallback words"]
