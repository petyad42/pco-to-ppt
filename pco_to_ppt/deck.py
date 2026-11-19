"""Build a .pptx lyrics deck from songs, using example.pptx as the template base.

We open the example deck so the output inherits its slide master, layouts, Arial
theme and 16:9 size, then strip the example's own slides and add our own. Lyric
text goes into the title placeholder (matching the example, whose lyrics sit in
the title placeholder -- a Google Slides export quirk we match deliberately), at
36pt Arial, centered. A blank (empty-title) separator slide is inserted between
songs.
"""

from __future__ import annotations

import os
from typing import List

from pptx import Presentation
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE, PP_ALIGN
from pptx.util import Emu, Pt

from .chunking import DEFAULT_MAX_LINES, chunk_sections
from .models import Song

# slideLayout2 in example.pptx is the lyric/title layout. python-pptx exposes
# layouts by index on the first slide master.
LYRIC_LAYOUT_INDEX = 1
TITLE_FONT_SIZE_PT = 36
TITLE_FONT_NAME = "Arial"

# The layout's title box is only ~0.92" tall, so 3-4 lines of 36pt text overflow
# it, and viewers like Keynote/Google Slides push the overflow downward (text no
# longer vertically centered). Each lyric slide therefore gets a full-height box
# anchored to the middle. Horizontal position/width match the template.
BOX_LEFT = Emu(311700)
BOX_WIDTH = Emu(8520600)
BOX_VERTICAL_MARGIN = Emu(228600)  # 0.25" top and bottom


def _strip_slides(prs: Presentation) -> None:
    """Remove every slide from a presentation, keeping masters/layouts/theme.

    Dropping entries from the slide-id list alone is not enough: the slide parts
    and the presentation's relationships to them stay in the package, so newly
    added slides collide on names like ``slide1.xml`` and produce a corrupt file
    with duplicate zip members. For each slide we drop the presentation->slide
    relationship (which also releases the orphaned slide part) and the id-list
    entry.
    """
    xml_slides = prs.slides._sldIdLst  # noqa: SLF001 - documented python-pptx access
    rid_attr = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
    part = prs.part
    for sld_id in list(xml_slides):
        rid = sld_id.get(rid_attr)
        if rid is not None and rid in part.rels:
            part.drop_rel(rid)
        xml_slides.remove(sld_id)


def _lyric_layout(prs: Presentation):
    layouts = prs.slide_layouts
    if LYRIC_LAYOUT_INDEX < len(layouts):
        return layouts[LYRIC_LAYOUT_INDEX]
    return layouts[0]


def _set_title(slide, text: str, slide_height: int) -> None:
    """Put ``text`` into the slide's title placeholder as centered 36pt Arial.

    The placeholder is resized to the full slide height (minus margins) and its
    text anchored to the middle, so the lyrics sit at the vertical center in any
    viewer. Multi-line text is written as one paragraph per line so each lyric
    line keeps its own line on the slide.
    """
    title = slide.shapes.title
    if title is None:
        return
    title.left = BOX_LEFT
    title.width = BOX_WIDTH
    title.top = BOX_VERTICAL_MARGIN
    title.height = Emu(slide_height - 2 * BOX_VERTICAL_MARGIN)

    tf = title.text_frame
    tf.clear()
    tf.word_wrap = True
    tf.vertical_anchor = MSO_ANCHOR.MIDDLE
    # Shrink-on-overflow, applied by PowerPoint for unusually long slides.
    tf.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE
    lines = text.split("\n") if text else [""]
    for i, line in enumerate(lines):
        para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        para.alignment = PP_ALIGN.CENTER
        run = para.add_run()
        run.text = line
        run.font.size = Pt(TITLE_FONT_SIZE_PT)
        run.font.name = TITLE_FONT_NAME


def build_presentation(
    songs: List[Song],
    template_path: str,
    max_lines: int = DEFAULT_MAX_LINES,
) -> Presentation:
    """Build (but do not save) a Presentation of lyric slides for the songs."""
    prs = Presentation(template_path)
    _strip_slides(prs)
    layout = _lyric_layout(prs)
    slide_height = prs.slide_height

    for index, song in enumerate(songs):
        slide_texts = chunk_sections(song.sections, max_lines=max_lines)
        for text in slide_texts:
            slide = prs.slides.add_slide(layout)
            _set_title(slide, text, slide_height)
        # Blank separator between songs (not after the last one).
        if index < len(songs) - 1:
            sep = prs.slides.add_slide(layout)
            _set_title(sep, "", slide_height)

    return prs


def output_filename(plan_id: str) -> str:
    return f"plan_{plan_id}.pptx"


def build_deck(
    songs: List[Song],
    plan_id: str,
    template_path: str,
    out_dir: str = ".",
    max_lines: int = DEFAULT_MAX_LINES,
) -> str:
    """Build and save the deck; return the output path (overwrites if present)."""
    prs = build_presentation(songs, template_path, max_lines=max_lines)
    out_path = os.path.join(out_dir, output_filename(plan_id))
    prs.save(out_path)
    return out_path
