"""Agent + Store unit tests. Offline only: fake clients, no network."""
import re
import time

from backend.agent import parse_rule, evaluate_rule, check_rules, why_query, voice_log
from backend.readers import DEMO_INSTRUMENTS
from backend.store import Store


class RaisingClient:
    """Fake client whose model calls always fail -> forces local fallbacks."""

    def spark_open(self, *a, **k):
        raise RuntimeError("no network in tests")

    def wonder(self, *a, **k):
        raise RuntimeError("no network in tests")

    def transcribe(self, *a, **k):
        raise RuntimeError("no network in tests")


class WonderRaisingOnlyClient(RaisingClient):
    def __init__(self):
        self.wonder_calls = 0

    def wonder(self, *a, **k):
        self.wonder_calls += 1
        raise RuntimeError("wonder down")


def _seed_store(n=6, start=10.0, step=2.0):
    s = Store()
    base = time.time()
    for i in range(n):
        s.add_reading({
            "instrument_id": "gauge-1",
            "ts": base + i,
            "value": start + i * step,
            "unit": "PSI",
            "quality": "simulated",
        })
    return s


def test_parse_rule_temperature_below_regex():
    rule = parse_rule(
        "alert when temperature goes below 20", DEMO_INSTRUMENTS, RaisingClient()
    )
    assert rule["instrument_id"] == "thermo-1"
    assert rule["op"] == "<"
    assert rule["threshold"] == 20


def test_evaluate_rule_fires_and_misses():
    assert evaluate_rule({"op": "<", "threshold": 20}, 15) is True
    assert evaluate_rule({"op": "<", "threshold": 20}, 25) is False
    assert evaluate_rule({"op": ">", "threshold": 80}, 90) is True
    assert evaluate_rule({"op": ">", "threshold": 80}, 10) is False


def test_check_rules_firing():
    rule = parse_rule(
        "alert when temperature goes below 20", DEMO_INSTRUMENTS, RaisingClient()
    )
    latest = {
        "thermo-1": {"instrument_id": "thermo-1", "ts": time.time(), "value": 15,
                     "unit": "C", "quality": "simulated"},
        "gauge-1": {"instrument_id": "gauge-1", "ts": time.time(), "value": 10,
                    "unit": "PSI", "quality": "simulated"},
    }
    alerts = check_rules([rule], latest)
    assert len(alerts) == 1
    assert alerts[0]["kind"] == "alert"
    assert alerts[0]["rule_id"] == rule["id"]
    assert "thermo-1" in alerts[0]["message"]


def test_check_rules_no_fire():
    rule = parse_rule(
        "alert when temperature goes below 20", DEMO_INSTRUMENTS, RaisingClient()
    )
    latest = {
        "thermo-1": {"instrument_id": "thermo-1", "ts": time.time(), "value": 25,
                     "unit": "C", "quality": "simulated"},
    }
    assert check_rules([rule], latest) == []


def test_why_query_fallback_when_wonder_raises():
    store = _seed_store()
    client = WonderRaisingOnlyClient()
    res = why_query("Why did pressure rise?", store, client, [])
    assert client.wonder_calls >= 1
    assert res["evidence"], "fallback must still return grounded evidence"
    assert res["question"] == "Why did pressure rise?"
    assert "fallback" in res["model"]
    # Answer must cite a concrete number from the stats.
    assert re.search(r"\d", res["answer"]), f"answer cites no number: {res['answer']!r}"


def test_voice_log_transcript_path():
    ev = voice_log(transcript="pressure looks high, keeping watch", client=RaisingClient())
    assert ev["kind"] == "voice_log"
    assert ev["transcript"] == "pressure looks high, keeping watch"
    assert ev["ts"] > 0


def test_voice_log_empty_raises():
    try:
        voice_log(transcript="", client=None)
    except ValueError:
        return
    raise AssertionError("expected ValueError for empty transcript")


def test_store_stats_trend():
    s = Store()
    base = time.time()
    for i in range(5):
        s.add_reading({"instrument_id": "gauge-1", "ts": base + i * 60,
                       "value": float(i * 10), "unit": "PSI", "quality": "simulated"})
    st = s.stats("gauge-1")
    assert st["current"] == 40
    assert st["change"] == 40
    assert st["trend_per_min"] > 0
    assert st["min"] == 0 and st["max"] == 40
