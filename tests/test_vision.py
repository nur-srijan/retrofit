import io, math
import pytest
PIL = pytest.importorskip("PIL"); np = pytest.importorskip("numpy")
from PIL import Image, ImageDraw
from backend.vision import extract_features

GAUGE = {"id":"gauge-1","type":"gauge","unit":"PSI","range":{"min":0,"max":100},
         "bbox":{"x":0.1,"y":0.1,"w":0.8,"h":0.8},"calibration":{"min_angle_deg":-120,"max_angle_deg":120}}

def dial_png(angle_deg, size=300):
    img = Image.new("RGB", (size, size), "white"); d = ImageDraw.Draw(img)
    cx = cy = size/2; R = size*0.42
    d.ellipse([cx-R, cy-R, cx+R, cy+R], outline="black", width=3)
    for a in range(-120, 121, 30):
        r = math.radians(a); x, y = cx + R*0.88*math.sin(r), cy - R*0.88*math.cos(r)
        d.line([cx + R*0.78*math.sin(r), cy - R*0.78*math.cos(r), x, y], fill="black", width=2)
    r = math.radians(angle_deg)
    d.line([cx, cy, cx + R*0.7*math.sin(r), cy - R*0.7*math.cos(r)], fill="black", width=6)
    d.ellipse([cx-6, cy-6, cx+6, cy+6], fill="black")
    buf = io.BytesIO(); img.save(buf, format="PNG"); return buf.getvalue()

@pytest.mark.parametrize("angle", [-90.0, -30.0, 0.0, 45.0, 90.0])
def test_needle_angle_within_5deg(angle):
    f = extract_features(dial_png(angle), GAUGE)
    assert abs(f["needle_angle_deg"] - angle) <= 5, f

def test_light_brightness_reacts():
    dark = Image.new("RGB", (100, 100), (5, 5, 5)); bright = Image.new("RGB", (100, 100), (250, 250, 250))
    inst = {"type":"indicator_light","bbox":{"x":0,"y":0,"w":1,"h":1}}
    for img, want in [(dark, 0), (bright, 1)]:
        buf = io.BytesIO(); img.save(buf, format="PNG")
        assert abs(extract_features(buf.getvalue(), inst)["brightness"] - want) < 0.1

def test_garbage_raises_for_fallback():
    with pytest.raises(Exception):
        extract_features(b"not an image", GAUGE)
