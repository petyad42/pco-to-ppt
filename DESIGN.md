# pco-to-ppt — Design

## Goal

A CLI that pulls a Planning Center Online (PCO) service plan and generates a
PowerPoint lyrics deck matching the existing `example.pptx` style. Built now for
single-user (CLI) use, structured so a web app can reuse the core later.

## Shape & structure

- **Python 3**, reusing dependencies from `jsonparser.py` where they fit.
- **Library core + thin interactive CLI.** The library has three concerns:
  1. PCO fetch
  2. lyric chunking
  3. pptx build

  The CLI is a thin wrapper over the library.
- `requirements.txt`: `requests`, `python-dotenv`, `python-pptx`, `rich`,
  `progressbar`, `unidecode`.
- No web code now, but the core stays web-reusable.

## PCO fetching

Lifted from `jsonparser.py`; the Ableton `.als` half is dropped (it belongs to a
different project).

- **Auth**: `PCO_TOKEN` from `.env`, sent as the `Authorization` header.
  - The web app will later need proper OAuth — deferred.
- **Input**: interactive prompt for a service link, or ENTER to use the example
  service — exactly like the original script.
  - **This prompt is the web-app seam.** It gets a code comment marking where
    input handling changes for the web version.
- Parse the plan ID from the URL (or raw input).
- Fetch `/services/v2/plans/{id}/items`, paginate via `links.next`, filter to
  `item_type == "song"`, and **preserve plan order** (service running order).
- **Non-song items are ignored.**
- For each song, fetch the arrangement's **`sections`**
  (`/services/v2/songs/{song_id}/arrangements/{arrangement_id}/sections`), which
  returns objects with `label`, `lyrics`, and `breaks_at`.
  - **Fall back** to the arrangement's raw `lyrics` field when sections are
    absent.
  - Note: `sections` is a separate API call from the arrangement endpoint that
    returns BPM/meter, so this adds one more request per song.
- Keep the **Rich table** (title / key / meter / BPM) as a pre-generation
  confirmation of what was found.

## Lyric chunking → slides

- One section maps to **one or more** slides.
- Split a section only when it exceeds **max-lines-per-slide** (default **4**,
  configurable). The default matches the example deck, which tops out at 4 lines.
- Break on **line boundaries only** — never mid-line.
- **Balance** chunks evenly rather than greedy-packing:
  - 9 lines at max 4 → `5 + 4` or `3 + 3 + 3`, not `4 + 4 + 1`.
- **No labels** on slides — pure lyrics.
- **Never run `unidecode` on lyric text** — preserve full Unicode / accents
  exactly (lyrics are e.g. Hungarian with accents). `unidecode` stays only on
  titles, for the table/filename.

## Deck generation

- Use **`example.pptx` as the `python-pptx` template base**: open it, strip its
  44 example slides, and inherit the master / `slideLayout2` / Arial theme /
  16:9 size (9144000 × 5143500 EMU).
- Lyric slides use the **title placeholder** on `slideLayout2`: **36 pt Arial,
  centered, autofit**.
  - This matches the example, whose lyric text sits in the `title` placeholder
    (a quirk of the Google Slides export). We match it so the look is identical,
    even though it is semantically odd.
- Insert **one empty-title separator slide between songs** (the example uses
  empty-title slides at positions 6, 14, 25 for this purpose).
- **One deck per service.**
- Output to the **current working directory** as `plan_<plan_id>.pptx`,
  overwriting if it already exists.

## Explicitly deferred (later branches)

- Web app
- OAuth
- Announcements and other non-song items
- Service-order / song-title slides
- Themes / alternate styling
- Max-lines-per-slide as a user-facing option beyond the default

## Source material

- `jsonparser.py` — existing script. Reuse its PCO fetch logic (token auth,
  plan-items fetch, pagination, song filter, arrangement resolution). Drop its
  Ableton `.als` section.
- `example.pptx` — the style reference and `python-pptx` template base.
