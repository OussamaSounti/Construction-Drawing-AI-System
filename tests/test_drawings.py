import pytest

from takeoff.drawings import find_anchors, parse_scale
from tests.test_ingest import span


@pytest.mark.parametrize("note, feet_per_inch", [
    ('SCALE: 1/4" = 1\'-0"', 4),
    ('1/4" = 1\'-0"', 4),
    ('SCALE: 1 1/2" = 1\'-0"', 2 / 3),
    ('SCALE: 3" = 1\'-0"', 1 / 3),
    ('SCALE: 12" = 1\'-0"', 1 / 12),
    ("SITE PLAN @ 1:20", 20 / 12),
])
def test_reads_the_scales_that_appear_on_real_sheets(note, feet_per_inch):
    assert parse_scale(note) == pytest.approx(feet_per_inch)


@pytest.mark.parametrize("note", ["NTS", "NOT TO SCALE", "N.T.S."])
def test_not_to_scale_has_no_scale(note):
    """These drawings cannot be measured, and must not be guessed at."""
    assert parse_scale(note) is None


def test_ignores_prose_about_scale():
    assert parse_scale("LARGER SCALE DRAWINGS SHALL TAKE PRECEDENCE OVER SMALLER ONES") is None


def test_each_scale_note_marks_a_drawing():
    """One sheet, several drawings: the notes are how we count them."""
    spans = [span('SCALE: 1/4" = 1\'-0"', x0=0.2, y0=0.8), span('SCALE: 1/4" = 1\'-0"', x0=0.6, y0=0.8)]
    assert len(find_anchors(spans)) == 2


def test_skips_notes_inside_the_title_block():
    spans = [span('SCALE: 1/4" = 1\'-0"', x0=0.2, y0=0.8), span('SCALE: 1/4" = 1\'-0"', x0=0.9, y0=0.9)]
    assert len(find_anchors(spans, title_block_edge=0.85)) == 1


def test_keeps_unmeasurable_drawings_flagged():
    anchors = find_anchors([span("NTS", x0=0.2, y0=0.8)])
    assert len(anchors) == 1 and not anchors[0].measurable
