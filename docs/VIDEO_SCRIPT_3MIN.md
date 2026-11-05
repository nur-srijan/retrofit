# Retrofit — Official 3-Minute Hackathon Demo Video Script

**Target Duration:** Exactly 2 minutes 50 seconds to 2 minutes 58 seconds (hard limit: 3:00).  
**Track:** Push the Frontier (Manufacturing, Energy, Physical Systems)  
**Bonus Flags:** Best Build on Meta Open-Weight Models ($10,000) · Best Agentic Use-Case ($5,000) · Most Viral ($20,000)

---

## 🛠️ Props & Screen Setup Before Hitting Record
1. **Screen:** Browser open to `http://localhost:8000` (full screen or clean 1080p window).
2. **Webcam:** Have your laptop camera ready.
3. **Props on desk:**
   - Your smartphone (screen on with flashlight toggle or a dial image).
   - A paper dial or an actual gauge/pump/watch (if handy, or just your phone showing a gauge).

---

## ⏱️ Video Script (Word-for-Word)

### [0:00 – 0:25] The Hook & Industrial Problem (Impact 30%)
* **Visual:** Speaker on camera for 5 seconds, then screen switches to Retrofit dark-mode dashboard (`http://localhost:8000`).
* **Spoken:**
> "Across factories, water utilities, and power plants, billions of dollars of critical infrastructure runs on legacy analog equipment — needle pressure gauges, temperature dials, and indicator lights. 
> 
> Replacing them with digital sensors requires taking facilities offline and costs thousands of dollars per panel. 
> 
> We built **Retrofit**: point any webcam or phone camera at an analog control panel, and it instantly transforms into a live, typed, queryable data stream — with autonomous agents monitoring operations."

---

### [0:25 – 0:55] Perception & Tool Compilation (Meta Models 25% + Technical Depth 20%)
* **Visual:** 
  - Click **Autopilot** (or **Detect**). 
  - Show the green SAM 3.1 perception bounding boxes and yellow Muse Spark tags snap onto the instruments.
  - Click **Compile** on the gauge to show the code editor expanding.
* **Spoken:**
> "Under the hood, we use Meta's foundational models across the entire pipeline.
> 
> First, **SAM 3.1** performs multi-object perception to segment every gauge and display in the frame simultaneously, while **Muse Spark** classifies the instrument types, units, and calibration ranges.
> 
> But here is our core architectural breakthrough: **the models compile themselves out of the loop.**
> 
> Rather than paying thousands of dollars in cloud latency to call an LLM on every video frame, **Muse Spark writes deterministic, sandboxed Python reader code on the fly**, rigorously verifies it against a held-out test suite, and compiles it for our local runtime. 
> 
> Zero marginal inference cost, 100% verified self-consistency, running at native frame rates."

---

### [0:55 – 1:35] The Physical Reality Moment (The 25% Demo Score / The "WOW" Factor)
* **Visual:**
  - Click **Camera** mode. 
  - Hold your phone with the flashlight turned on directly in front of the webcam over the indicator light box.
  - Flashlight ON $\to$ dashboard lamp flips to "ON" green.
  - Flashlight OFF $\to$ dashboard lamp flips to "OFF".
  - Show the needle gauge tracking your hand/dial movement live in the chart.
* **Spoken:**
> "Let's test physical reality. 
> 
> This is not a simulation. In Camera mode, our pipeline streams video frames into our real-time computer vision engine. 
> 
> Watch what happens when I shine my phone's flashlight at the camera — the indicator light immediately triggers to ON. When I turn it off, it drops back to OFF. 
> 
> And for analog dials, our radial line scanner tracks the needle angle in degrees and converts it through Spark's compiled reader into exact pressure PSI in real time. 
> 
> Real physical causality, streaming directly into a typed REST and WebSocket data bus."

---

### [1:35 – 2:15] Open-Weight Agent & Incident Summaries (Best Open-Weight + Best Agentic)
* **Visual:**
  - Type into rule box: `alert when pressure goes above 80`. Click **Add Rule**.
  - Show the compiled rule chip appear with its source model badge.
  - Pressure crosses threshold $\to$ red **ALERT** banner triggers in the feed $\to$ an automated **Incident Summary** generates underneath it.
* **Spoken:**
> "Now let's bring in autonomous operators.
> 
> For our rule engine, we deployed Meta's open-weight model, **Muse Spark Open**, hosted on **Baseten**. 
> 
> An operator simply types a natural language rule: *'alert when pressure goes above 80'*. Muse Spark Open compiles this into an executable predicate chip. 
> 
> When our camera detects pressure breaching 80 PSI, an alert fires instantly. 
> 
> But notice what happens next: **Muse Spark Open acts as an autonomous incident agent**, instantly analyzing the telemetry and issuing a verified operator action item directly into the operational feed."

---

### [2:15 – 2:40] Voice Logging & Cross-Series Reasoning (Muse Voice + Muse Wonder)
* **Visual:**
  - Click **Record** on the Voice panel $\to$ speak: *"Inspected valve three, pressure spike confirmed"* $\to$ click **Stop & Transcribe**.
  - Show the transcribed note appear in the event log stamped with `muse-voice-transcribe-1.0`.
  - In the "Why?" box, click **Ask** on *"Why did pressure drop?"* (or type a question).
  - Show Muse Wonder generate a multi-sentence diagnosis citing exact statistical evidence chips.
* **Spoken:**
> "Operators in the field can log spoken observations. We capture audio via the browser, convert to 16 kHz WAV, and stream it to **Muse Voice Transcribe** to tag events on the timeline.
> 
> Finally, when an engineer asks: *'Why did pressure spike at 14:00?'*, **Muse Wonder** reasons across all multi-instrument time series, correlations, and operator voice logs, providing a grounded root-cause diagnosis citing exact numerical evidence."

---

### [2:40 – 3:00] Closing & Architectural Integrity (Impact & Open Source)
* **Visual:**
  - Quickly flash the GitHub repository (`nur-srijan/retrofit`) and the architecture diagram in `docs/ARCHITECTURE.md`.
* **Spoken:**
> "Retrofit is 100% open source on GitHub, built entirely from scratch during this hackathon with full contract schemas and verified graceful fallbacks. 
> 
> By combining SAM 3.1, Muse Spark, Muse Spark Open on Baseten, Muse Voice, and Muse Wonder, we turn the physical world's legacy hardware into intelligent, connected infrastructure. 
> 
> Thank you!"

---

## 💡 Quick Tips for a Flawless Recording
1. **Rehearse once:** Do one dry run through the script without recording to get the timing down under 2m50s.
2. **Audio quality:** Use your wired earphones or AirPods mic if possible to keep audio crisp.
3. **If Wonder latency takes 8 seconds:** Don't wait silently! While the "Muse Wonder reasoning..." spinner appears, say: *"While Wonder calculates the cross-series variance, notice our architecture gracefully streams evidence tokens..."*
4. **Export:** Export as 1080p MP4 or record directly on Loom.

