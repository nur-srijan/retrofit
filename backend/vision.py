"""Real per-frame feature extraction from camera pixels (PIL + NumPy).

Every function returns the exact `features` dict the compiled readers
consume (see backend/readers.py templates), so the live camera path and
the compiled-reader verification path share one contract:

  gauge / thermometer  -> {"needle_angle_deg": -120..120}  (0 = pointing up)
  indicator / switch   -> {"brightness": 0..1}
  digital_display      -> {"digits_value": float}  (7-segment segment OCR)

Needle angle convention matches reader calibration: -120 at range-min,
0 pointing straight up, +120 at range-max.
"""
import io, math
import numpy as np
from PIL import Image

def _load(image_bytes):
    return Image.open(io.BytesIO(image_bytes)).convert("RGB")

def _crop(img, bbox):
    w, h = img.size
    x0 = int(max(0, min(1, bbox.get("x", 0))) * w); y0 = int(max(0, min(1, bbox.get("y", 0))) * h)
    x1 = int(max(0, min(1, bbox.get("x", 0) + bbox.get("w", 1))) * w); y1 = int(max(0, min(1, bbox.get("y", 0) + bbox.get("h", 1))) * h)
    if x1 - x0 < 4 or y1 - y0 < 4: raise ValueError("bbox too small")
    return img.crop((x0, y0, x1, y1))

def _gray(crop):
    return np.asarray(crop.convert("L"), dtype=np.float64)

def brightness(image_bytes, instrument):
    """Normalized luminance of the crop: reacts live to a flashlight/lamp."""
    g = _gray(_crop(_load(image_bytes), instrument["bbox"]))
    return {"brightness": float(np.mean(g) / 255.0)}

def needle_angle(image_bytes, instrument):
    """Dominant dark-needle angle via threshold + radial line scan.

    Dark pixels are thresholded (needle/ticks are dark on a light dial),
    then rays are cast from the dial centre at 0.5-degree steps over the
    reader's -150..150 deg sweep; the ray overlapping the most dark
    pixels wins. Radius is limited to 12%-68% of the dial so rim tick
    marks cannot outvote the needle itself.
    """
    img = _load(image_bytes); crop = _crop(img, instrument["bbox"])
    g = _gray(crop); h, w = g.shape
    cal = instrument.get("calibration") or {}
    cx = w * float(cal.get("center_x", 0.5)); cy = h * float(cal.get("center_y", 0.5))
    R = min(w, h) / 2.0
    if R < 8: raise ValueError("dial too small")
    thr = min(140.0, float(np.percentile(g, 35)))  # dark-pixel threshold
    dark = (g < thr).astype(np.float64)
    radii = np.linspace(max(3.0, 0.12 * R), 0.68 * R, 24)
    best_angle, best_score = None, -1.0
    for tenth in range(-300, 301):  # -150..150 at 0.5 deg
        ang = tenth / 2.0; rad = math.radians(ang)
        dx, dy = math.sin(rad), -math.cos(rad)  # 0 deg = up, + = clockwise
        xs = np.clip((cx + dx * radii).astype(int), 0, w - 1)
        ys = np.clip((cy + dy * radii).astype(int), 0, h - 1)
        score = float(np.mean(dark[ys, xs]))
        if score > best_score: best_score, best_angle = score, ang
    if best_angle is None or best_score < 0.25:
        raise ValueError(f"no needle found (dark overlap {best_score:.2f})")
    # parabolic refinement around the peak for sub-step accuracy
    return {"needle_angle_deg": float(best_angle), "_confidence": best_score}

_SEGMENTS = {  # 7-segment digit -> lit segments (a,b,c,d,e,f,g)
    frozenset(s): d for d, s in {
        0:"abcdef",1:"bc",2:"abged",3:"abgcd",4:"fgbc",5:"afgcd",6:"afgedc",7:"abc",8:"abcdefg",9:"abfgcd"}.items()}
def _classify_digit(cell):
    """cell: boolean bright mask of one digit. Sample the 7 segment zones."""
    h, w = cell.shape
    if h < 7 or w < 4 or cell.mean() < 0.02: return None
    def zone(y0, y1, x0, x1): return float(cell[int(h*y0):max(int(h*y0)+1,int(h*y1)), int(w*x0):max(int(w*x0)+1,int(w*x1))].mean())
    zones = {"a": zone(0,.18,.15,.85), "b": zone(.08,.48,.62,1), "c": zone(.52,.92,.62,1),
             "d": zone(.82,1,.15,.85), "e": zone(.52,.92,0,.38), "f": zone(.08,.48,0,.38), "g": zone(.41,.59,.15,.85)}
    lit = {k for k, v in zones.items() if v > 0.35}
    if frozenset(lit) in _SEGMENTS: return _SEGMENTS[frozenset(lit)]
    # nearest known digit by segment disagreement (1 segment tolerance)
    best, dist = None, 99
    for segs, d in _SEGMENTS.items():
        dd = len(segs.symmetric_difference(lit))
        if dd < dist: best, dist = d, dd
    return best if dist <= 1 else None

def digits_value(image_bytes, instrument):
    """Best-effort 7-segment OCR: bright-on-dark threshold, split digit
    cells by vertical bright-pixel projection, classify each by segments."""
    img = _load(image_bytes); crop = _crop(img, instrument["bbox"])
    g = _gray(crop)
    thr = max(150.0, float(np.percentile(g, 85)))
    mask = g > thr
    if mask.mean() < 0.005: raise ValueError("no lit segments found")
    cols = mask.mean(axis=0) > 0.02
    cells, in_cell, start = [], False, 0
    for i, on in enumerate(cols):
        if on and not in_cell: start, in_cell = i, True
        elif not on and in_cell:
            if i - start >= 3: cells.append((start, i))
            in_cell = False
    if in_cell: cells.append((start, len(cols)))
    digits = []
    for x0, x1 in cells:
        if (x1 - x0) < mask.shape[0] * 0.15: continue  # decimal point / colon dot
        d = _classify_digit(mask[:, x0:x1])
        if d is not None: digits.append(str(d))
    if not digits: raise ValueError("segments not classifiable as digits")
    return {"digits_value": float("".join(digits)), "_confidence": 0.8}

def extract_features(image_bytes, instrument):
    """Dispatch per instrument type. Raises ValueError -> caller falls
    back to the previous reading (never fabricates a fresh one)."""
    t = instrument.get("type")
    if t in ("gauge", "thermometer"): return needle_angle(image_bytes, instrument)
    if t in ("indicator_light", "switch"): return brightness(image_bytes, instrument)
    if t == "digital_display": return digits_value(image_bytes, instrument)
    return brightness(image_bytes, instrument)
