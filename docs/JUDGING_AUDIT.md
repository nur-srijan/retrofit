# Retrofit — Judging Audit (2026-11-05, Phase 3 repo as-is)
Rubric: `hackathon-details.md:213-219` (Impact 30 / Meta tooling 25 / Technical 20 / Demo 25, 0-10 each); bonuses `:249-259`.
Method: read `README.md`, `docs/ARCHITECTURE.md`, `docs/DEMO_SCRIPT.md`, `docs/FALLBACKS.md`, skimmed all of `backend/`+`frontend/` (~445 LOC). Scores are honest estimates, not results.

## Verdict in one paragraph
Strong, legible concept ("model compiles itself out of the loop") with unusually honest fallback disclosure, but judges will probe one weak spot: on the default demo path most Meta models are bypassed or only loosely coupled to what is on screen (simulator + templates + Web Speech), so the pitch currently outruns the visible evidence. Fixes below are ranked to close exactly that gap.

## Meta-model truth table — does each do real, visible work?
| Model | Real work in code | Visible in demo? | Honest verdict |
|---|---|---|---|
| SAM 3.1 | `backend/meta_clients.py:37` streams `sam-3.1` `/v1/responses`; `backend/readers.py:58` calls it per concept (4x) | **Barely** | Boxes are only counted: `sam_found` merely flips `source` to `sam+spark`; every bbox/label/`track_id` shown comes from Spark JSON or demo defaults (`readers.py:58-77`, `frontend/app.js:6` overlay). No frame-to-frame tracking despite "tracks" in `docs/DEMO_SCRIPT.md:3`. Returns empty on some/synthetic images (`docs/FALLBACKS.md:2,5`) -> Spark-vision fallback silently carries detection. |
| Muse Spark | Vision classify/calibrate JSON (`readers.py:58`); generates `read()` code, safety-checked + verified (`readers.py:39`) | **Yes, on demand** | Most credible model use. Caveat: streaming demo calls `compile_reader(inst, None)` (`backend/app.py:35`), i.e. local templates, until a human clicks Compile. Verification is self-consistency, not ground truth: `verify()` (`readers.py:29`) feeds synthetic features from `features_for()` (`readers.py:23`), the exact inverse of the reader — near-tautological 100% PASS, no pixels ever read. |
| Muse Spark Open (Baseten) | `backend/meta_clients.py:30` Baseten-first, Meta-Spark fallback; used in `parse_rule()` (`backend/agent.py:13`) | **Yes, small** | Verified config: `.env` has `BASETEN_API_KEY`, `SPARK_OPEN_MODEL=meta-models/muse-spark-open-1026`; app loads `.env` via `_load_dotenv()` (`meta_clients.py:3`); `docs/FALLBACKS.md:8` records live OK 2026-11-05; UI shows `spark_open_source` + per-rule `source_model`. But its only job (NL->one JSON predicate) is provably regex-replaceable (`tests/test_readers.py` regex test passes offline). |
| Muse Wonder | `why_query()` (`backend/agent.py:40`) sends locally computed stats + recent events, renders answer + evidence chips | **Yes** | Real and grounded in `Store.all_stats()` numbers, with local-stats fallback. Weakness: evidence is aggregate stats only (no timestamps/alignment), yet prompt asks for "likely cause" — on a sinusoidal simulator it can only narrate correlation; say so on stage. |
| Muse Voice Transcribe | Real multipart client `transcribe()` (`meta_clients.py:61`) via `POST /api/voice` `audio_base64` (`backend/app.py:97`) | **No (default path)** | Frontend never records/sends audio: `voiceBtn` uses browser `SpeechRecognition` only (`frontend/app.js:18`), `voiceSend` posts text. Demo therefore shows the Web Speech fallback (`agent.py:58` labels it `browser-webspeech`), not the Meta model. |

## 1. Impact (30%) — est. 6/10
- Have: clean Push-the-Frontier fit (`README.md:2` manufacturing/energy); typed schema + REST/WS API (`backend/app.py` `/api/schema|readings`, `contracts/*.json`) is a plausible "camera in, API out" product surface; 4-instrument rig is relatable.
- Have: problem framing in `docs/DEMO_SCRIPT.md:1` (analog panels unlogged/unqueryable) is instantly understood.
- Gap: zero real-world validation — no real panel photo benchmark, no accuracy vs ground truth (see tautology above), no user/pilot, no quantified benefit (cost vs PLC retrofit, time saved). All stored data is in-memory deques (`backend/store.py`), no persistence/export.
- Gap: architecture promises MQTT (`docs/ARCHITECTURE.md:15,31`) — not implemented anywhere in `backend/`; judges checking code will find REST+WS only.

## 2. Creative use of Meta models (25%) — est. 6/10
- Have: genuinely inventive core idea — Spark writes deterministic reader code once, runtime is local (`docs/ARCHITECTURE.md` principles 1-2); five Meta models each assigned a distinct layer is above basic-integration level.
- Have: fallback honesty is a differentiator: `backend/app.py` `FALLBACKS`, `docs/FALLBACKS.md`, `generated_by`/`source_model`/`model` fields disclose which model actually ran.
- Gap: SAM 3.1 — the most "surprise us" model — contributes no visible artifact (above). Health badges also overclaim: `frontend/app.js` lights all five badges from `meta_key_present` alone.
- Gap: `docs/ARCHITECTURE.md:29` claims compiler retries "until under error threshold"; `compile_reader()` tries exactly one candidate, then template. No Muse Image/Glimmer use (not required, but narrows "creative" surface).

## 3. Technical depth & execution (20%) — est. 5/10
- Have: contract-first JSON (`contracts/`, 6 schemas), small readable modules, sandboxed-ish reader exec (`_safe()` bans imports/`__`, restricted builtins in `run_compiled`), deterministic stats in `store.py`, offline tests for readers/rules/store (`tests/test_readers.py`).
- Gap: no pixel pipeline at all — needle angle/digits/brightness are synthesised from the simulated value (`demo_value()` `app.py:22` -> `features_for()`), so "compiled readers read the panel" is inverted in demo mode; camera-detected instruments would still be fed synthetic/midpoint values by the simulator.
- Gap: no git history (`git log`: no commits yet), no CI, in-memory state, `exec()` of model code remains a review flag, 1 Hz simulator vs "high FPS" claim (`docs/ARCHITECTURE.md:30`).

## 4. Demo (25%) — est. 6/10 if rehearsed live, 4/10 as-is
- Have: tight 3-min script (`docs/DEMO_SCRIPT.md`), one-click Demo Panel, every beat maps to a UI panel; "demo never hard-fails" fallback design is real.
- Gap: default path is a DOM simulator, not a camera/panel — a judge asking "show it on a real gauge" exposes that detect-on-camera and live readings are disconnected (above). Script line `0:20` implies SAM/Spark ran when Start-Demo alone returns `demo-fallback` instruments.
- Gap: alert beat is timing-fragile — gauge is sinusoidal (`app.py:23`), so ">80" crossing may not occur on cue within the scripted ~30s; compile beat needs a live Spark call (up to 90s timeout in `meta_clients.py`) if not pre-compiled.
- Gap: no demo video/recording artifact in repo; submission depends entirely on live execution.

## Bonus: Best Open-Weight Build ($10K) — plausible flag, weak frontrunner
- Have: eligible stack verified end-to-end (Baseten + `meta-models/muse-spark-open-1026`, `.env` loaded by app, disclosed fallback, partner-verifiable via `/api/health` `spark_open_source`). This clears the verification bar in `hackathon-details.md:256`.
- Gap: open-weight model does the smallest, most replaceable job in the system; "best build on" implies centrality it does not have. `.env` is gitignored, so judges need the health endpoint/screenshot as evidence — never commit the key.

## Bonus: Best Agentic Use-Case ($5K) — plausible, currently under-staged
- Have: real agent ingredients — Spark compiles+verifies tools (readers), Spark Open compiles NL intent to predicates, rules then fire autonomously every 1s in `simulator()`/`check_rules()` with cooldown + broadcast, Wonder reasons over all series + events.
- Gap: no autonomy loop is visible: human clicks detect, compile, rule, why separately; no planning, chaining, or retry; "Agent Trace" is a timestamped event log, not steps/decisions/tool calls. Autonomy is present in code, absent in narrative.

## Concrete fixes, ranked by demo visibility (~1 hour total)
1. **(15m) Make SAM visible or stop claiming it:** return SAM boxes from `/api/detect` and draw them in a second colour beside Spark boxes; if SAM returns empty, show "SAM: 0 boxes -> Spark-vision fallback" live. Turns the known empty-result weakness into a transparency beat.
2. **(10m) One "Autopilot" button:** chain detect -> compile all -> create default rule -> on alert auto-ask Wonder, rendering numbered agent-trace steps (tool, model, result). Single highest lift for Agentic bonus + Demo.
3. **(10m) Real voice path:** `MediaRecorder` -> `audio_base64` -> existing `transcribe()`; display returned `source` so judges see `muse-voice-transcribe-1.0`, keeping Web Speech as labelled fallback.
4. **(10m) Give Spark Open a second, load-bearing job:** on alert, Spark Open writes the incident summary/action into the feed (with `source_model`). Makes Open-Weight central to the loop, not just parsing.
5. **(5m) Deterministic alert timing:** start demo phase so pressure crosses 80 ~20s after rule creation (offset `t0` or threshold-aware start); show the compiled predicate chip + latest value counting toward it.
6. **(5m) Honest verification label:** rename UI text to "self-consistency on held-out synthetic features" and show `generated_by` prominently; pre-click Compile before recording so the Spark-generated code (not template) is what ships on screen.
7. **(5m) Evidence pack for judges:** screenshot `/api/health` (shows Baseten source), fix badges to per-model last-call status, align `docs/ARCHITECTURE.md` (drop MQTT + "retry", or implement the retry loop in `compile_reader()` — 3 attempts is ~15 lines).
