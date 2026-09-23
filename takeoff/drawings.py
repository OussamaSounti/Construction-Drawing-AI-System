"""Find the individual drawings on a sheet, and what scale each is drawn at.

A permit sheet is not one drawing. It carries several -- floor plans, details,
elevations -- each with its own scale note underneath ("SCALE: 1/4" = 1'-0").
Those notes are the anchors: one note means one drawing, and the note says how
many real feet an inch of paper stands for, which is what turns pixel lengths
into a quantity takeoff.
"""

import re
from dataclasses import dataclass

# 1/4" = 1'-0"  |  1 1/2" = 1'-0"  |  3" = 1'-0"  |  12" = 1'-0"
ARCHITECTURAL = re.compile(
    r"""(?P<paper>\d+\s+\d+/\d+|\d+/\d+|\d+(?:\.\d+)?)\s*"?\s*=\s*
        (?P<feet>\d+)\s*'\s*(?:-\s*(?P<inches>\d+)\s*"?)?""",
    re.VERBOSE,
)
# @ 1:20, drawn at a plain ratio
RATIO = re.compile(r"\b1\s*:\s*(?P<ratio>\d+)\b")
NOT_TO_SCALE = ("NTS", "N.T.S.", "NOT TO SCALE")

# Scale notes are short labels. General notes that merely discuss scale
# ("LARGER SCALE DRAWINGS SHALL TAKE PRECEDENCE") are prose, so length alone
# keeps them out.
MAX_NOTE = 40


def measure(fraction):
    """Read '1 1/2' or '3/4' or '3' as a number of inches."""
    whole, _, rest = fraction.strip().partition(" ")
    if "/" in whole:
        numerator, _, denominator = whole.partition("/")
        return int(numerator) / int(denominator)
    total = float(whole)
    if rest and "/" in rest:
        numerator, _, denominator = rest.partition("/")
        total += int(numerator) / int(denominator)
    return total


def parse_scale(text):
    """Feet of building represented by one inch of paper, or None.

    None covers both "not to scale" and anything unrecognised: a drawing whose
    scale is unknown cannot be measured, and saying so is the point.
    """
    text = text.strip()
    if len(text) > MAX_NOTE or any(n in text for n in NOT_TO_SCALE):
        return None

    match = ARCHITECTURAL.search(text)
    if match:
        paper = measure(match["paper"])
        feet = int(match["feet"]) + int(match["inches"] or 0) / 12
        return feet / paper if paper else None

    match = RATIO.search(text)
    if match:
        return int(match["ratio"]) / 12
    return None


@dataclass
class Anchor:
    """A scale note, and so a drawing on the sheet."""

    text: str
    feet_per_inch: float | None
    x: float
    y: float

    @property
    def measurable(self):
        return self.feet_per_inch is not None


def find_anchors(spans, title_block_edge=None):
    """Locate every scale note in the drawing area of the sheet."""
    anchors = []
    for span in spans:
        if len(span.text) > MAX_NOTE:
            continue
        if title_block_edge and span.x0 > title_block_edge:
            continue
        scale = parse_scale(span.text)
        if scale or any(n in span.text for n in NOT_TO_SCALE):
            anchors.append(Anchor(span.text, scale, span.x, span.y))
    return anchors
