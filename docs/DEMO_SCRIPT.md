# 3-minute demo script
0:00 Problem: factory/energy panels are analog, unlogged, unqueryable. Retrofit = camera in, API out.
0:20 Click 🤖 Autopilot: SAM 3.1 + Spark detect (SAM box count shown, fallback disclosed if empty) -> Spark compiles+verifies all readers -> Spark Open rule -> live. Or Start Demo Panel manually (or camera at bike-pump gauge + thermometer + phone stopwatch + lamp). SAM 3.1 tracks, Muse Spark classifies/calibrates -> 4 typed instruments overlay.
0:50 Live cards + chart streaming. Note: models compiled themselves out of the loop - runtime is local readers @1Hz+.
1:10 Reader Compiler: compile gauge reader - Muse Spark-generated code + verification report 100% PASS on held-out cases.
1:40 NL rule (Spark Open on Baseten, fallback disclosed): "alert when pressure goes above 80" -> compiled predicate chip -> wait for crossing -> ALERT fires.
2:10 Voice log: speak "checked pump, pressure climbing" -> Muse Voice Transcribe event in feed.
2:30 "Why did pressure drop?" -> Muse Wonder answers grounded in evidence chips (current/change/trend per series).
2:55 Close: public repo, contracts, fallbacks - every model step degrades gracefully, demo never hard-fails.
