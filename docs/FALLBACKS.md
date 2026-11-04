# Fallbacks (decided Phase 0, 2026-11-04 smoke tests)
Verified live: `muse-spark-1.3` + `muse-wonder-1.0` chat completions at https://api.meta.ai/v1 (MODEL_API_KEY, 200 OK; use max_tokens>=300 as reasoning tokens consume budget). SAM 3.1 `sam-3.1` POST /v1/responses streaming returns special-token box/mask text (needs meta_sam_parser); returns empty for non-matching synthetic images. Muse Voice Transcribe `muse-voice-transcribe-1.0` POST /v1/asr/transcribe (multipart) / wss://api.meta.ai/v1/asr/realtime.
| Capability | Primary | Fallback (demo never hard-fails) |
|---|---|---|
| SAM 3.1 perception | sam-3.1 per concept, streamed | Muse Spark vision whole-frame JSON boxes -> demo instruments (simulated panel) |
| Spark classify/calibrate | muse-spark-1.3 vision JSON | Heuristic defaults per type + manual click-to-calibrate in UI |
| Reader compiler | muse-spark-1.3 generates read() code | Local deterministic templates per reader_type; code still shown + verified |
| Spark Open rules | Baseten meta-models/muse-spark-open-1026 (needs BASETEN_API_KEY - VERIFIED 2026-11-05: key in .env, spark_open returned OK via meta-models/muse-spark-open-1026 via Baseten) | regex parser only if Baseten+Meta both fail - source_model field always discloses which ran |
| Wonder why? | muse-wonder-1.0 grounded on computed stats | Local stats/correlation template answer citing same evidence[] |
| Voice log | muse-voice-transcribe-1.0 upload | Browser Web Speech API transcript -> POST /api/voice {transcript} |
| Runtime | Compiled readers on features | Simulator produces plausible gauge/temp/stopwatch/light series through same readers |
