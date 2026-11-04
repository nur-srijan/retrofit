"""SAM 3.1 segmentation text parser (pure stdlib).

SAM 3.1 via Meta ``POST /v1/responses`` (streaming) returns segmentation as
special-token text rather than structured JSON. Depending on prompt/model
behaviour the box coordinates may appear as:

1. JSON objects with ``x_min``/``y_min``/``x_max``/``y_max`` in 0..1000 space,
   e.g. ``{"x_min": 100, "y_min": 150, "x_max": 400, "y_max": 500}``
2. bare special tokens grouped sequentially,
   e.g. ``<x_min=100><y_min=150><x_max=400><y_max=500>``
3. plain arrays, e.g. ``[100, 150, 400, 500]``

:func:`parse_sam_text` handles all three, normalises coordinates to 0..1
(top-left origin, matching ``contracts/instrument.json``), clamps
out-of-range values and drops degenerate (zero/negative-area) boxes.
Unparseable, empty or garbage input yields ``[]`` -- never raises.
"""

import re

_DEFAULT_CONFIDENCE = 0.9

_COORD_KEYS = ("x_min", "y_min", "x_max", "y_max")
_CONF_KEYS = ("confidence", "conf", "score")

# {...} candidate spans (no nesting needed for flat box dicts).
_JSON_OBJ_RE = re.compile(r"\{[^{}]*\}")
# key-value pairs inside a JSON-ish object: "x_min": 123 / 'x_min' = 123
_KV_RE = re.compile(
    r"['\"]?(x_min|y_min|x_max|y_max|confidence|conf|score)['\"]?"
    r"\s*[:=]\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)"
)
# bare special tokens: x_min=123 (optionally wrapped in <...> by the model).
_TOKEN_RE = re.compile(
    r"(x_min|y_min|x_max|y_max|confidence|conf|score)"
    r"\s*=\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)"
)
# plain arrays: [x1, y1, x2, y2] with optional 5th confidence element.
_ARRAY_RE = re.compile(
    r"\[\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s*,\s*"
    r"([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s*,\s*"
    r"([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)\s*,\s*"
    r"([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?)"
    r"(?:\s*,\s*([-+]?\d*\.?\d+(?:[eE][-+]?\d+)?))?\s*\]"
)


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _norm_coord(value, dim):
    """Map a raw coordinate to 0..1 (unclamped).

    SAM emits 0..1000 pixel-space values; values already in 0..1 are kept
    as-is so callers passing normalised arrays also work.
    """
    if abs(value) > 1.0:
        return value / dim
    return value


def _clamp01(value):
    return max(0.0, min(1.0, value))


def _confidence_from(mapping):
    for key in _CONF_KEYS:
        if key in mapping:
            conf = _to_float(mapping[key])
            if conf is None:
                continue
            if conf > 1.0:  # e.g. 0..100 style score
                conf = conf / 100.0 if conf <= 100.0 else 1.0
            return _clamp01(conf)
    return _DEFAULT_CONFIDENCE


def _make_box(x1, y1, x2, y2, confidence, image_w, image_h):
    nx1 = _clamp01(_norm_coord(x1, image_w))
    ny1 = _clamp01(_norm_coord(y1, image_h))
    nx2 = _clamp01(_norm_coord(x2, image_w))
    ny2 = _clamp01(_norm_coord(y2, image_h))
    w = nx2 - nx1
    h = ny2 - ny1
    if w <= 0 or h <= 0:
        return None
    return {
        "bbox": {"x": nx1, "y": ny1, "w": w, "h": h},
        "confidence": confidence,
    }


def _mask_spans(text, spans):
    chars = list(text)
    for start, end in spans:
        for i in range(max(0, start), min(len(chars), end)):
            chars[i] = " "
    return "".join(chars)


def parse_sam_text(text, image_w=1000, image_h=1000):
    """Parse SAM 3.1 special-token/JSON/array box text into instruments.

    Args:
        text: raw model output text (str or bytes).
        image_w: image width the 0..1000 coords refer to.
        image_h: image height the 0..1000 coords refer to.

    Returns:
        list of ``{"bbox": {"x","y","w","h"}, "confidence": float,
        "track_id": int}`` with normalised 0..1 coords. ``[]`` on
        empty/garbage input. Never raises.
    """
    try:
        if isinstance(text, (bytes, bytearray)):
            text = bytes(text).decode("utf-8", errors="ignore")
        if not isinstance(text, str) or not text.strip():
            return []
        try:
            image_w = float(image_w)
        except (TypeError, ValueError):
            image_w = 1000.0
        try:
            image_h = float(image_h)
        except (TypeError, ValueError):
            image_h = 1000.0
        if not image_w or image_w <= 0:
            image_w = 1000.0
        if not image_h or image_h <= 0:
            image_h = 1000.0

        boxes = []
        consumed = []

        # Pass 1: JSON-ish objects {"x_min":..,"y_min":..,"x_max":..,"y_max":..}.
        for match in _JSON_OBJ_RE.finditer(text):
            pairs = _KV_RE.findall(match.group(0))
            if not pairs:
                continue
            mapping = {}
            for key, raw in pairs:
                value = _to_float(raw)
                if value is not None:
                    mapping[key] = value
            if not all(k in mapping for k in _COORD_KEYS):
                continue
            box = _make_box(
                mapping["x_min"], mapping["y_min"],
                mapping["x_max"], mapping["y_max"],
                _confidence_from(mapping), image_w, image_h,
            )
            if box is not None:
                boxes.append(box)
                consumed.append(match.span())

        masked = _mask_spans(text, consumed)

        # Pass 2: bare special tokens grouped sequentially
        # (<x_min=..><y_min=..><x_max=..><y_max=..>, any order/spacing).
        token_matches = list(_TOKEN_RE.finditer(masked))
        current = {}
        group_start = None
        group_end = None

        def _flush():
            if all(k in current for k in _COORD_KEYS):
                box = _make_box(
                    current["x_min"], current["y_min"],
                    current["x_max"], current["y_max"],
                    _confidence_from(current), image_w, image_h,
                )
                if box is not None:
                    boxes.append(box)
                    if group_start is not None:
                        consumed.append((group_start, group_end))

        for idx, tok in enumerate(token_matches):
            key, raw = tok.group(1), tok.group(2)
            value = _to_float(raw)
            if value is None:
                continue
            if key in current and key in _COORD_KEYS:
                # A repeated coord key starts a new box; flush first.
                _flush()
                current = {}
                group_start = None
            if group_start is None:
                group_start = tok.start()
            group_end = tok.end()
            current[key] = value
            if all(k in current for k in _COORD_KEYS):
                is_last = idx == len(token_matches) - 1
                next_key = None if is_last else token_matches[idx + 1].group(1)
                # Hold the flush if a trailing confidence token follows so
                # it stays attached to this box.
                if next_key is None or next_key not in _CONF_KEYS:
                    _flush()
                    current = {}
                    group_start = None
        # Handle a trailing complete group ending with a confidence token.
        _flush()

        masked = _mask_spans(text, consumed)

        # Pass 3: plain [x1, y1, x2, y2] arrays (optional 5th = confidence).
        for match in _ARRAY_RE.finditer(masked):
            vals = [_to_float(g) for g in match.groups() if g is not None]
            if len(vals) < 4 or any(v is None for v in vals[:4]):
                continue
            conf = _DEFAULT_CONFIDENCE
            if len(vals) == 5 and vals[4] is not None:
                conf = _clamp01(vals[4] / 100.0 if vals[4] > 1.0 else vals[4])
            box = _make_box(vals[0], vals[1], vals[2], vals[3],
                            conf, image_w, image_h)
            if box is not None:
                boxes.append(box)

        for i, box in enumerate(boxes):
            box["track_id"] = i + 1
        return boxes
    except Exception:
        return []
