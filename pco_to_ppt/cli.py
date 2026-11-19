"""Interactive command-line entry point.

This is the thin wrapper over the library. Run with:

    python -m pco_to_ppt

It prompts for a service link (or ENTER for the example), fetches songs, shows a
confirmation table, and writes the deck.
"""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress
from rich.table import Table

from . import pco_fetch
from .deck import build_deck

EXAMPLE_SERVICE = "https://services.planningcenteronline.com/plans/91675400"

# Path to the style template, relative to the repo root (one level up from this
# package). The output deck inherits this file's master/layout/theme.
TEMPLATE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "example.pptx")


def _prompt_for_plan() -> str:
    # -- WEB-APP SEAM -------------------------------------------------------
    # For the CLI, the plan link comes from an interactive prompt. When this
    # grows into a web app, THIS is the single place that changes: replace the
    # input() call below with the request/form value. Everything downstream
    # (parse_plan_id, fetch, deck build) already takes plain arguments and needs
    # no change.
    # -----------------------------------------------------------------------
    user_input = input("Please enter service link or press ENTER to use example service: ")
    return user_input.strip() or EXAMPLE_SERVICE


def _song_table(songs) -> Table:
    table = Table(title="Songs")
    for col in ("#", "Title", "Key", "Meter", "BPM"):
        table.add_column(col)
    for i, song in enumerate(songs, start=1):
        table.add_row(
            str(i),
            str(song.title),
            str(song.key_name),
            str(song.meter),
            str(song.bpm),
            style="bright_green",
        )
    return table


def main() -> int:
    load_dotenv()
    console = Console()

    try:
        token = pco_fetch.get_token()
    except RuntimeError as exc:
        console.print(f"[red]{exc}[/red]")
        return 1

    raw = _prompt_for_plan()
    try:
        plan_id = pco_fetch.parse_plan_id(raw)
    except ValueError as exc:
        console.print(f"[red]{exc}[/red]")
        return 1

    console.print("Retrieving songs from Planning Center...")
    try:
        songs = pco_fetch.fetch_plan_songs(plan_id, token)
    except Exception as exc:  # noqa: BLE001 - surface any HTTP/parse error to the user
        console.print(f"[red]Failed to fetch plan items: {exc}[/red]")
        return 1

    if not songs:
        console.print("[yellow]No songs found in this plan.[/yellow]")
        return 1

    with Progress() as progress:
        task = progress.add_task("Fetching lyrics...", total=len(songs))
        for song in songs:
            try:
                pco_fetch.enrich_song(song, token)
            except Exception as exc:  # noqa: BLE001
                console.print(f"[yellow]Could not enrich {song.title!r}: {exc}[/yellow]")
            progress.advance(task)

    console.print(_song_table(songs))

    out_path = build_deck(songs, plan_id, TEMPLATE_PATH)
    console.print(f"[green]Saved deck to {out_path}[/green]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
