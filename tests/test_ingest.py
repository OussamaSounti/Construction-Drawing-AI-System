import pytest

from takeoff.ingest import Span, classify, clean, title_block


def span(text, size=10, x0=0.1, y0=0.1, width=0.05):
    return Span(size, clean(text), x0, y0, x0 + width, y0 + 0.02)


def test_clean_folds_ligatures():
    assert clean("ﬂoor  plan") == "FLOOR PLAN"


def test_reads_sheet_number_from_the_title_block():
    spans = [span("A101", size=80, x0=0.92, y0=0.94), span("FLOOR PLAN - LEVEL 1", size=24, x0=0.9, y0=0.88)]
    assert classify(spans) == ("floor_plan", "A101")


def test_ignores_door_tags_out_in_the_drawing():
    """Door and window tags look like sheet numbers but sit mid-drawing."""
    spans = [span("X27", size=10, x0=0.48, y0=0.21), span("A1-101", size=38, x0=0.93, y0=0.96),
             span("FLOOR PLAN 1", size=25, x0=0.9, y0=0.6)]
    assert classify(spans)[1] == "A1-101"


def test_title_wins_over_a_passing_mention():
    """The title block is set in larger type than a note mentioning a plan."""
    spans = [span("EXTERIOR ELEVATIONS", size=24, x0=0.9, y0=0.9),
             span("SEE FLOOR PLAN FOR DETAIL", size=8, x0=0.2, y0=0.3)]
    assert classify(spans)[0] == "elevation"


def test_title_block_edge_is_the_corridor_before_the_sheet_number():
    spans = [span("A101", size=80, x0=0.92, y0=0.94), span("BEDROOM", x0=0.3, y0=0.4),
             span("DINING", x0=0.6, y0=0.4, width=0.06)]
    assert title_block(spans) == pytest.approx(0.66)


def test_no_title_block_when_text_runs_up_to_the_edge():
    """Dense sheets leave no corridor; callers must handle None."""
    spans = [span("A101", size=80, x0=0.92, y0=0.94), span("KEYNOTES", x0=0.89, y0=0.5, width=0.02)]
    assert title_block(spans) is None
