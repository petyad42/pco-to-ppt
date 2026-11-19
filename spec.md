## Problem Statement

Each week I prepare a worship service in Planning Center Online (PCO). To present
the songs, I currently have to copy lyrics out of PCO by hand and lay them out in
PowerPoint, matching a specific slide style. This is slow, repetitive, and
error-prone — especially getting the lyrics split across slides so they stay
readable at presentation font size.

## Solution

A command-line tool, `pco-to-ppt`, that takes a PCO service plan, pulls its songs
and lyrics, and generates a PowerPoint lyrics deck that matches my existing
presentation style (based on `example.pptx`). I run it before a service, confirm
the song list it found, and get a ready-to-present `.pptx`.

The tool is built as a reusable library with a thin interactive CLI on top, so a
web app can reuse the core later without a rewrite.

## User Stories

1. As a worship presenter, I want to paste a PCO service plan link into the tool, so that I don't have to find song lyrics manually.
2. As a worship presenter, I want to press ENTER to use a known example service, so that I can test the tool without typing a link.
3. As a worship presenter, I want the tool to accept either a full PCO service URL or a bare plan ID, so that I can use whichever I have on hand.
4. As a worship presenter, I want the tool to authenticate to PCO using a token from a `.env` file, so that I don't have to enter credentials each run.
5. As a worship presenter, I want the tool to fetch all song items in the plan, so that no song is missed.
6. As a worship presenter, I want songs retrieved across all paginated API pages, so that long services are fully covered.
7. As a worship presenter, I want only song items included, so that headers, media, and announcements don't clutter the deck.
8. As a worship presenter, I want songs ordered exactly as they appear in the plan, so that the deck follows the service running order.
9. As a worship presenter, I want lyrics pulled from each song arrangement's sections, so that the words come pre-chunked into verses and choruses.
10. As a worship presenter, I want the tool to fall back to the arrangement's raw lyrics field when sections are missing, so that songs without structured sections still produce slides.
11. As a worship presenter, I want each section placed on its own slide, so that the deck structure follows the song structure.
12. As a worship presenter, I want a section that is too long to be split across multiple slides, so that text stays large and readable during presentation.
13. As a worship presenter, I want splitting to default to a maximum of 4 lines per slide, so that slides match my existing deck's density.
14. As a worship presenter, I want the maximum lines per slide to be configurable, so that I can adjust density if needed.
15. As a worship presenter, I want splits to happen only on line boundaries, so that no line of lyrics is ever cut in the middle.
16. As a worship presenter, I want multi-slide sections balanced evenly, so that I don't get a near-empty trailing slide (9 lines become 5+4, not 4+4+1).
17. As a worship presenter, I want no section labels shown on slides, so that slides show pure lyrics with a clean look.
18. As a worship presenter, I want lyric text kept exactly as PCO returns it, including accented characters, so that non-English lyrics display correctly.
19. As a worship presenter, I want a blank separator slide inserted between songs, so that there is a clear visual gap when moving from one song to the next.
20. As a worship presenter, I want the deck to reuse my `example.pptx` style, so that output matches my existing presentations without manual restyling.
21. As a worship presenter, I want lyric slides rendered at 36pt Arial, centered, matching the template, so that the look is consistent.
22. As a worship presenter, I want one PowerPoint file produced per service, so that I have a single deck to present from.
23. As a worship presenter, I want the output named `plan_<plan_id>.pptx` in the current directory, so that I can find it predictably.
24. As a worship presenter, I want the output overwritten if it already exists, so that re-running regenerates cleanly.
25. As a worship presenter, I want to see a table of the songs found (title, key, meter, BPM) before the deck is generated, so that I can confirm the tool read the plan correctly.
26. As a future developer, I want the PCO fetch and slide generation in a library separate from the CLI, so that a web app can reuse the core.
27. As a future developer, I want the interactive input step clearly marked in code, so that I know where to change input handling when building the web app.

## Implementation Decisions

- **Project shape.** A small Python 3 package: a library core with three concerns
  — PCO fetch, lyric chunking, pptx build — and a thin interactive CLI entry
  point. Dependencies: `requests`, `python-dotenv`, `python-pptx`, `rich`,
  `progressbar`, `unidecode`. Shipped with a `requirements.txt`.

- **Source material.** PCO fetch logic is lifted from the existing `jsonparser.py`
  (token auth, plan-items fetch, pagination, song filter, arrangement
  resolution). The script's Ableton `.als` section is dropped entirely — it
  belongs to a different project. `example.pptx` is the style reference and the
  `python-pptx` template base.

- **Authentication.** `PCO_TOKEN` read from `.env` via `python-dotenv`, sent as
  the `Authorization` header, matching the current script. OAuth is deferred to
  the web-app work.

- **Input.** Interactive prompt: enter a service link, or press ENTER for the
  example service. The input is parsed into a plan ID, accepting either a full
  PCO URL or a bare ID. This prompt is the designated web-app seam and must carry
  a code comment marking where input handling changes for the web version.

- **Fetching.** Call `GET /services/v2/plans/{id}/items`, follow `links.next` for
  pagination, filter to `item_type == "song"`, preserve plan order. Non-song
  items are ignored. For each song, fetch the arrangement's sections
  (`/services/v2/songs/{song_id}/arrangements/{arrangement_id}/sections`), which
  returns objects with `label`, `lyrics`, and `breaks_at`. Fall back to the
  arrangement's raw `lyrics` field when sections are absent. Note this is an
  additional request per song beyond the arrangement call that returns BPM/meter.

- **Confirmation UI.** Keep the Rich table (title, key, meter, BPM) shown before
  deck generation, as in the original script.

- **Lyric chunking.** A pure function takes a section (label + lyrics text) and a
  max-lines value and returns an ordered list of slide text blocks. Rules: one
  section maps to one or more slides; split only when the line count exceeds the
  max (default 4, configurable); break on line boundaries only, never mid-line;
  balance chunks evenly rather than greedy-packing (9 lines → 5+4 or 3+3+3, not
  4+4+1); no labels emitted onto slides. Lyric text is never passed through
  `unidecode` — full Unicode and accents are preserved. `unidecode` remains only
  for titles used in the table/filename.

- **Deck generation.** Open `example.pptx` as the `python-pptx` template base,
  strip its example slides, and inherit its master, `slideLayout2`, Arial theme,
  and 16:9 size (9144000 × 5143500 EMU). Lyric slides use the title placeholder
  on `slideLayout2`: 36pt Arial, centered, autofit. This matches the example,
  whose lyric text sits in the `title` placeholder (a Google Slides export quirk)
  — matched deliberately. Insert one empty-title separator slide between songs.
  One deck per service, written to the current directory as `plan_<plan_id>.pptx`,
  overwriting if present.

## Testing Decisions

A good test here asserts externally observable behavior — given inputs produce
expected outputs — not internal structure. Tests target the two seams agreed with
the developer:

- **Lyric chunking (primary seam, pure function).** The bulk of behavior is
  verified here with no network and no PowerPoint. Cover: a short section stays on
  one slide; a section over the max splits; splits land only on line boundaries
  (no line ever cut); even balancing (9 lines at max 4 → 5+4 or 3+3+3, never
  4+4+1); no labels appear in output; accented characters survive unchanged; a
  configurable max other than 4 is honored.

- **PCO fetch (boundary seam, JSON fixtures).** Tested by feeding captured PCO
  response JSON (plan items, arrangement, sections) into the fetch function rather
  than making live HTTP calls. Cover: song filtering (non-song items excluded),
  pagination across multiple pages via `links.next`, plan-order preservation, and
  the sections→raw-lyrics fallback.

There is no prior art in this repo (greenfield rewrite of a flat script), so these
establish the testing pattern. No automated test is placed on the pptx binary
output — its correctness is a manual visual check — nor on the interactive prompt.

## Out of Scope

- The web app itself (the core is only structured to allow it later).
- OAuth authentication.
- Announcements and any non-song plan items.
- Service-order or song-title slides.
- Alternate themes or styling beyond the `example.pptx` template.
- Automated testing of the generated `.pptx` binary and of the interactive prompt.
- Max-lines-per-slide as anything beyond a simple configurable value with default 4.

## Further Notes

- The existing `jsonparser.py` and `example.pptx` live in the repo root and are the
  reference inputs; `DESIGN.md` captures the same decisions as this spec in prose.
- Lyrics in the sample deck are Hungarian with accented characters, which is why
  accent preservation (no `unidecode` on lyrics) is called out explicitly.
- `sections` being a separate sub-resource means song count directly affects
  request count; not a concern at service scale but worth knowing.
