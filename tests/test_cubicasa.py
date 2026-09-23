from pathlib import Path

from takeoff.cubicasa import load_sample

FIXTURE = Path(__file__).parent / "fixture"


def test_finds_every_object_once():
    sample = load_sample(FIXTURE)
    counts = {k: len(sample.of(k)) for k in ("Wall", "Door", "Window", "Room")}
    assert counts == {"Wall": 1, "Door": 1, "Window": 1, "Room": 1}


def test_keeps_the_subtype():
    sample = load_sample(FIXTURE)
    assert sample.of("Wall")[0].subtype == "External"
    assert sample.of("Door")[0].subtype == "Swing Beside"
    assert sample.of("Room")[0].subtype == "Bath"


def test_outline_is_the_objects_own_polygon():
    """A wall takes its own outline, not the nested window's; a room takes its
    outline, not a nested dimension mark's."""
    sample = load_sample(FIXTURE)
    assert sample.of("Wall")[0].bbox == (0, 80, 300, 100)
    assert sample.of("Room")[0].bbox == (0, 0, 100, 80)


def test_points_are_image_pixels():
    """Coordinates are used as-is; the svg width/height must not rescale them."""
    sample = load_sample(FIXTURE)
    assert sample.of("Window")[0].points[0] == (40, 80)
    assert sample.image.name == "F1_scaled.png"
