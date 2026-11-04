"""Tests for backend.sam_parser.parse_sam_text (SAM 3.1 special-token text)."""
import pytest

from backend.sam_parser import parse_sam_text


def test_json_objects_1000_space():
    text = (
        'found [{"x_min": 100, "y_min": 150, "x_max": 400, "y_max": 500}, '
        '{"x_min": 600, "y_min": 50, "x_max": 900, "y_max": 300}]'
    )
    boxes = parse_sam_text(text)
    assert len(boxes) == 2
    b0 = boxes[0]
    assert b0["bbox"] == pytest.approx(
        {"x": 0.1, "y": 0.15, "w": 0.3, "h": 0.35}
    )
    assert b0["confidence"] == pytest.approx(0.9)
    assert b0["track_id"] == 1
    assert boxes[1]["track_id"] == 2
    assert boxes[1]["bbox"]["x"] == pytest.approx(0.6)


def test_json_object_with_confidence():
    boxes = parse_sam_text(
        '{"x_min": 100, "y_min": 100, "x_max": 200, "y_max": 200,'
        ' "confidence": 0.75}'
    )
    assert len(boxes) == 1
    assert boxes[0]["confidence"] == pytest.approx(0.75)


def test_special_tokens_grouped_sequentially():
    text = (
        "mask <x_min=100><y_min=150><x_max=400><y_max=500> and "
        "<x_min=600> <y_min=50> <x_max=900> <y_max=300> done"
    )
    boxes = parse_sam_text(text)
    assert len(boxes) == 2
    assert boxes[0]["bbox"]["x"] == pytest.approx(0.1)
    assert boxes[0]["bbox"]["w"] == pytest.approx(0.3)
    assert boxes[1]["bbox"]["x"] == pytest.approx(0.6)
    assert [b["track_id"] for b in boxes] == [1, 2]


def test_special_tokens_with_confidence():
    boxes = parse_sam_text(
        "<x_min=100><y_min=100><x_max=200><y_max=200><confidence=0.82>"
    )
    assert len(boxes) == 1
    assert boxes[0]["confidence"] == pytest.approx(0.82)


def test_plain_arrays():
    boxes = parse_sam_text("detections: [100, 150, 400, 500]")
    assert len(boxes) == 1
    assert boxes[0]["bbox"] == pytest.approx(
        {"x": 0.1, "y": 0.15, "w": 0.3, "h": 0.35}
    )
    assert boxes[0]["track_id"] == 1


def test_garbage_returns_empty():
    for junk in [
        "",
        "   ",
        "hello world",
        "no boxes here [[[ }}}",
        "<x_min=abc><y_min=???",
        "[1, 2, 3]",
        '{"foo": "bar"}',
    ]:
        assert parse_sam_text(junk) == []
    assert parse_sam_text(None) == []


def test_clamps_out_of_range():
    boxes = parse_sam_text(
        '{"x_min": -50, "y_min": -20, "x_max": 2000, "y_max": 1500}'
    )
    assert len(boxes) == 1
    for v in boxes[0]["bbox"].values():
        assert 0.0 <= v <= 1.0
    assert boxes[0]["bbox"]["x"] == pytest.approx(0.0)
    assert boxes[0]["bbox"]["y"] == pytest.approx(0.0)


def test_drops_degenerate_boxes():
    # zero width
    assert parse_sam_text(
        '{"x_min": 100, "y_min": 100, "x_max": 100, "y_max": 200}'
    ) == []
    # inverted coords
    assert parse_sam_text("[400, 400, 100, 100]") == []
    # zero-area tokens
    assert parse_sam_text(
        "<x_min=50><y_min=50><x_max=50><y_max=50>"
    ) == []


def test_custom_image_dims():
    boxes = parse_sam_text("[500, 250, 1000, 500]", image_w=2000, image_h=1000)
    assert len(boxes) == 1
    assert boxes[0]["bbox"] == pytest.approx(
        {"x": 0.25, "y": 0.25, "w": 0.25, "h": 0.25}
    )
