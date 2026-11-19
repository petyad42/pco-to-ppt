"""pco-to-ppt: generate a PowerPoint lyrics deck from a Planning Center Online plan.

The package is split into a reusable library core and a thin CLI:

- ``pco_fetch``  -- talk to the PCO API, return an ordered list of songs with lyrics.
- ``chunking``   -- pure lyric-to-slide splitting logic (no I/O).
- ``deck``       -- build a .pptx from songs, using example.pptx as the template.
- ``cli``        -- interactive command-line entry point (the web-app seam).

The library modules take plain data and return plain data / files, so a future
web app can reuse them without touching the CLI.
"""

from .models import Song, Section

__all__ = ["Song", "Section"]
