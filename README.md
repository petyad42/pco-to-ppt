# pco-to-ppt

Generate a PowerPoint lyrics deck from a Planning Center Online (PCO) service plan.

Point it at a PCO service plan, it pulls the songs and their lyrics, and writes a
`.pptx` whose style matches `example.pptx` (36pt Arial, centered, 16:9), with a
blank separator slide between songs.

## Setup

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Put your PCO personal access token in a `.env` file at the repo root:

```
PCO_TOKEN=<your token>
```

`.env` is gitignored, so the token is not committed.

## Run

```sh
python -m pco_to_ppt
```

It prompts for a service link (or press ENTER to use the built-in example), shows
a table of the songs it found, and writes `plan_<plan_id>.pptx` to the current
directory (overwriting if it already exists). The prompt accepts either a full PCO
service URL or a bare plan ID.

## How it works

The code is a reusable library core with a thin interactive CLI on top:

- `pco_to_ppt/pco_fetch.py` — talk to the PCO API; parsing functions are pure and
  fixture-testable, HTTP is isolated in `fetch_*` functions.
- `pco_to_ppt/chunking.py` — pure lyric-to-slide splitting: one section per slide,
  split only when over the max line count (default 4), break on line boundaries
  only, balance chunks evenly, no labels, accents preserved.
- `pco_to_ppt/deck.py` — build the `.pptx` from songs using `example.pptx` as the
  template base.
- `pco_to_ppt/cli.py` — the interactive entry point. The input prompt is marked as
  the single seam to change when this grows into a web app.

See `DESIGN.md` for the full design and the tracking issue for the spec.

## Tests

```sh
pytest
```

Tests cover the two seams: the pure chunking logic and the PCO fetch parsing
(against JSON fixtures, no network, no token needed). The generated `.pptx` is
verified by a manual visual check, not an automated test.
