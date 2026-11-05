import pytest
from backend.store import Store
from backend.readers import detect_instruments

def test_store_to_csv():
    s = Store()
    s.add_reading({"instrument_id": "gauge-1", "ts": 1700000000.0, "value": 42.5, "unit": "PSI", "quality": "camera"})
    s.add_reading({"instrument_id": "light-1", "ts": 1700000001.0, "value": 1.0, "unit": "", "quality": "camera"})
    csv = s.to_csv()
    lines = csv.strip().split("\n")
    assert len(lines) == 3
    assert lines[0] == "timestamp_iso,timestamp_unix,instrument_id,value,unit,quality"
    assert "gauge-1" in lines[1]
    assert "42.5" in lines[1]
    assert "light-1" in lines[2]

def test_empty_detection_without_client():
    # If a real image was provided but no model/client detected instruments, return empty list
    items, src = detect_instruments("data:image/jpeg;base64,123", None)
    assert items == []
    assert src == "none-detected"

def test_demo_detection_without_image():
    # When image is empty string, return demo instruments fallback
    items, src = detect_instruments("", None)
    assert len(items) == 4
    assert src == "demo-fallback"
