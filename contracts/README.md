# Contracts (source of truth)
All layers communicate only via these JSON shapes. Coordinates are normalized 0..1 (top-left origin).
- instrument.json: SAM 3.1 perception + Muse Spark understanding output
- reading.json: Runtime -> Data Bus -> Dashboard (WebSocket `kind:reading`)
- compiled_reader.json: Muse Spark Reader Compiler output + verification report
- rule.json: Muse Spark Open (Baseten) NL rule -> compiled predicate
- why.json: Muse Wonder cross-series reasoning, grounded in computed stats (evidence[])
- events.json: WebSocket envelope for readings/alerts/voice logs
Changing a contract requires orchestrator approval.
