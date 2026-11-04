# Retrofit
Point a camera at a legacy control panel -> every instrument becomes a live, typed, queryable data stream.
**Track:** Push the Frontier (manufacturing/energy). See docs/ARCHITECTURE.md, contracts/, docs/FALLBACKS.md.
## Quickstart
```bash
cp .env.example .env  # fill MODEL_API_KEY (dev.meta.ai), optionally BASETEN_API_KEY
pip install -r requirements.txt
uvicorn backend.app:app --port 8000   # or: python -m backend.app
# open http://localhost:8000
```
Demo without a physical panel: click **Start Demo Panel** - a simulated gauge + thermometer + stopwatch + indicator light run through the same compiled readers, charts, rules and why-queries.
## Built during the hackathon
All code in this repo was written during the Meta Global AI Developer Hackathon building period (Oct 27-Nov 4, 2026). No pre-existing project code was used; only public Meta model APIs and standard libraries.
## Meta models used (each does visible work)
SAM 3.1 (perception/tracking) - Muse Spark (classify, calibrate, write+verify reader code) - Muse Spark Open via Baseten (NL rule agent, with disclosed fallback) - Muse Wonder (why-queries) - Muse Voice Transcribe (operator voice log, Web Speech fallback).
## Architecture
Camera -> SAM 3.1 perception -> Muse Spark understanding -> Reader Compiler (Spark writes+verifies code) -> local Runtime -> typed Data Bus (REST+WebSocket) -> Operator Agent (Spark Open rules, Wonder why?, Voice log) -> Dashboard. Full diagram: docs/ARCHITECTURE.md. Contracts: contracts/. Fallbacks: docs/FALLBACKS.md. Demo script: docs/DEMO_SCRIPT.md.
## API
`GET /api/health` `POST /api/detect` `POST /api/compile` `GET /api/schema` `GET /api/readings` `POST /api/demo/start|stop` `POST/GET/DELETE /api/rules` `POST /api/why` `POST /api/voice` `WS /ws/stream`
## Tests
`.venv/bin/python -m pytest tests/ -q` and `python scripts/smoke_meta.py` (needs MODEL_API_KEY).
