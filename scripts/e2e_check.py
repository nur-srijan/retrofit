#!/usr/bin/env python3
"""Stdlib-only end-to-end check against a running Retrofit server.

Usage: python3 scripts/e2e_check.py [--base http://localhost:8000]
"""
import argparse
import json
import sys
import time
import urllib.error
import urllib.request


def http_get(base, path, timeout=10):
    req = urllib.request.Request(base + path, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, json.loads(r.read().decode())


def http_post(base, path, body, timeout=15):
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        base + path, data=data, method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        raw = r.read().decode()
        try:
            return r.status, json.loads(raw)
        except json.JSONDecodeError:
            return r.status, {"_raw": raw}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://localhost:8000")
    args = ap.parse_args()
    base = args.base.rstrip("/")
    failures = 0

    def step(name, fn):
        nonlocal failures
        try:
            detail = fn()
            print(f"[PASS] {name}" + (f" - {detail}" if detail else ""))
        except AssertionError as e:
            failures += 1
            print(f"[FAIL] {name} - {e}")
        except Exception as e:
            failures += 1
            print(f"[FAIL] {name} - {type(e).__name__}: {e}")

    def s_health():
        status, body = http_get(base, "/api/health")
        assert status == 200, f"HTTP {status}"
        assert body.get("status") == "ok", f"body={body}"
        return f"instruments={body.get('instruments')}"

    def s_demo_start():
        status, body = http_post(base, "/api/demo/start", {})
        assert status == 200, f"HTTP {status}: {body}"
        assert body.get("ok") is True or body.get("demo") is True, f"body={body}"
        return "demo started"

    def s_readings():
        last = None
        for _ in range(15):
            time.sleep(1)
            status, body = http_get(base, "/api/readings")
            assert status == 200, f"HTTP {status}"
            readings = body.get("readings", {})
            with_data = [k for k, v in readings.items() if v]
            last = f"{len(with_data)} instruments with data"
            if len(with_data) >= 3:
                return last
        raise AssertionError(f"only got: {last}")

    def s_rules():
        status, body = http_post(base, "/api/rules", {"text": "alert when pressure goes above 80"})
        assert status == 200, f"HTTP {status}: {body}"
        assert body.get("instrument_id") == "gauge-1", f"body={body}"
        assert body.get("op") == ">", f"body={body}"
        return f"{body.get('instrument_id')} {body.get('op')} {body.get('threshold')}"

    def s_voice():
        status, body = http_post(base, "/api/voice", {"transcript": "e2e check voice note"})
        assert status == 200, f"HTTP {status}: {body}"
        assert body.get("kind") == "voice_log", f"body={body}"
        assert body.get("transcript") == "e2e check voice note", f"body={body}"
        return "voice_log stored"

    def s_why():
        status, body = http_post(base, "/api/why", {"question": "Why did pressure change?"})
        assert status == 200, f"HTTP {status}: {body}"
        ev = body.get("evidence", [])
        assert isinstance(ev, list) and len(ev) > 0, f"empty evidence: {body}"
        assert body.get("answer"), f"empty answer: {body}"
        return f"evidence={len(ev)}"

    step("GET /api/health", s_health)
    step("POST /api/demo/start", s_demo_start)
    step("wait + GET /api/readings (>=3 instruments)", s_readings)
    step("POST /api/rules", s_rules)
    step("POST /api/voice", s_voice)
    step("POST /api/why (evidence non-empty)", s_why)

    if failures:
        print(f"{failures} step(s) FAILED")
        return 1
    print("All e2e steps PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
