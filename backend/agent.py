import re, json, time
OPS={">":lambda a,b:a>b,"<":lambda a,b:a<b,">=":lambda a,b:a>=b,"<=":lambda a,b:a<=b,"==":lambda a,b:a==b,"!=":lambda a,b:a!=b}
WORD_OPS={"above":">","over":">","exceeds":">","below":"<","under":"<","drops below":"<","goes above":">","goes below":"<",">":">","<":"<",">=":">=","<=":"<="}
def _match_instrument(text, instruments):
    t=text.lower()
    for inst in instruments:
        tokens=[inst["id"].lower(), inst["label"].lower(), inst["type"].replace("_"," ")]
        # distinctive words: pressure, thermometer/temp, stopwatch/time, light
        extra={"gauge-1":["pressure","gauge","psi","pump"],"thermo-1":["temperature","thermometer","temp","kitchen"],"stopwatch-1":["stopwatch","time","seconds","timer"],"light-1":["light","indicator","lamp"]}
        tokens+=extra.get(inst["id"],[])
        if any(tok and tok in t for tok in tokens): return inst
    return instruments[0] if instruments else None
def parse_rule(text, instruments, client=None):
    if client is not None:
        try:
            listing=", ".join(f"{i['id']} ({i['label']}, {i['type']}, {i['unit']})" for i in instruments)
            content,src=client.spark_open([{"role":"user","content":f"Convert this alert rule to ONLY JSON {{\"instrument_id\":\"...\",\"op\":\">\",\"threshold\":0,\"message\":\"...\"}} using instruments: {listing}. Rule: {text}"}], max_tokens=1500)
            d=json.loads(re.search(r"\{.*\}",content,re.S).group(0))
            if d["instrument_id"] in [i["id"] for i in instruments] and d["op"] in OPS:
                return {"id":f"rule-{int(time.time())}","text":text,"instrument_id":d["instrument_id"],"op":d["op"],"threshold":float(d["threshold"]),"duration_s":0,"message":d.get("message") or text,"source_model":src}
        except Exception: pass
    m=re.search(r"([a-zA-Z ]+?)\s*(>=|<=|>|<|above|over|below|under|exceeds|goes above|goes below|drops below)\s*(-?\d+(?:\.\d+)?)", text, re.I)
    if not m: raise ValueError("Could not parse rule. Try: 'alert when pressure goes above 80'")
    inst=_match_instrument(text, instruments)
    if not inst: raise ValueError("No instruments known yet - detect or start demo first")
    op=WORD_OPS.get(m.group(2).lower(), m.group(2)); src="local regex parser (fallback)"
    if client is not None:
        try: _,src0=client.spark_open([{"role":"user","content":"ping"}], max_tokens=300); src=src0+" + regex fallback"
        except Exception: pass
    return {"id":f"rule-{int(time.time()*1000)}","text":text,"instrument_id":inst["id"],"op":op,"threshold":float(m.group(3)),"duration_s":0,"message":text,"source_model":src}
def evaluate_rule(rule, value):
    try: return OPS[rule["op"]](float(value), float(rule["threshold"]))
    except Exception: return False
def check_rules(rules, latest):
    out=[]
    for r in rules:
        rd=latest.get(r["instrument_id"])
        if rd and evaluate_rule(r, rd["value"]): out.append({"kind":"alert","ts":time.time(),"rule_id":r["id"],"message":f"ALERT: {r['instrument_id']} = {rd['value']} {r['op']} {r['threshold']} - {r['text']}","reading":rd})
    return out
def why_query(question, store, client=None, events=None):
    stats=store.all_stats(); evidence=[]
    for iid,s in stats.items():
        if not s: continue
        for k in ("current","change","trend_per_min","min","max"):
            if k in s: evidence.append({"instrument_id":iid,"stat":k,"value":s[k]})
    if not evidence: return {"question":question,"answer":"No readings yet. Start the demo panel or camera detection first, wait a few seconds, then ask again.","evidence":[],"model":"muse-wonder-1.0 (no data)"}
    biggest=None
    for iid,s in stats.items():
        if s and "change" in s and (biggest is None or abs(s["change"])>abs(stats[biggest]["change"])): biggest=iid
    if client is not None:
        try:
            ans=client.wonder([{"role":"user","content":f"You are Muse Wonder doing cross-series reasoning. Answer ONLY using these computed stats, cite exact numbers, explain likely cause and what else changed at the same time. Stats: {json.dumps(stats)}. Recent events: {json.dumps((events or [])[-5:])}. Question: {question}"}], max_tokens=2000)
            if ans: return {"question":question,"answer":ans,"evidence":evidence,"model":"muse-wonder-1.0"}
        except Exception: pass
    s=stats.get(biggest,{}) if biggest else {}
    answer=f"Based on the live series, {biggest} moved most: from {s.get('first')} to {s.get('current')} (change {s.get('change')}, trend {s.get('trend_per_min')}/min, range {s.get('min')}-{s.get('max')}). Other series now: "+", ".join(f"{k}={v.get('current')}" for k,v in stats.items() if v)+". This correlation in the recorded window is the grounded explanation available; check the alert/voice events for operator actions at that time."
    return {"question":question,"answer":answer,"evidence":evidence,"model":"muse-wonder-1.0 (fallback: local stats)"}
def voice_log(transcript=None, client=None, audio_bytes=None):
    source="browser-webspeech"
    if audio_bytes and client is not None:
        transcript=client.transcribe(audio_bytes); source="muse-voice-transcribe-1.0"
    if not transcript: raise ValueError("empty transcript")
    return {"kind":"voice_log","ts":time.time(),"transcript":transcript,"source":source}
