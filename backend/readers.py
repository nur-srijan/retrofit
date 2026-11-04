import json, re, math, random
DEMO_INSTRUMENTS=[
 {"id":"gauge-1","label":"Bike Pump Pressure","type":"gauge","unit":"PSI","range":{"min":0,"max":100},"bbox":{"x":0.05,"y":0.12,"w":0.38,"h":0.55},"confidence":0.96,"track_id":1,"calibration":{"min_angle_deg":-120,"max_angle_deg":120},"source":"demo-fallback"},
 {"id":"thermo-1","label":"Kitchen Thermometer","type":"gauge","unit":"C","range":{"min":0,"max":100},"bbox":{"x":0.48,"y":0.12,"w":0.22,"h":0.55},"confidence":0.93,"track_id":2,"calibration":{"min_angle_deg":-120,"max_angle_deg":120},"source":"demo-fallback"},
 {"id":"stopwatch-1","label":"Phone Stopwatch","type":"digital_display","unit":"s","range":{"min":0,"max":60},"bbox":{"x":0.74,"y":0.15,"w":0.22,"h":0.30},"confidence":0.95,"track_id":3,"calibration":{},"source":"demo-fallback"},
 {"id":"light-1","label":"Indicator Light","type":"indicator_light","unit":"","range":{"min":0,"max":1},"bbox":{"x":0.74,"y":0.55,"w":0.16,"h":0.22},"confidence":0.97,"track_id":4,"calibration":{"threshold":0.5},"source":"demo-fallback"},
]
TEMPLATES={
 "gauge":"def read(features):\n    angle = features['needle_angle_deg']\n    frac = (angle - {min_a}) / ({max_a} - {min_a})\n    frac = max(0.0, min(1.0, frac))\n    return {mn} + frac * ({mx} - {mn})",
 "thermometer":"def read(features):\n    angle = features['needle_angle_deg']\n    frac = (angle - {min_a}) / ({max_a} - {min_a})\n    frac = max(0.0, min(1.0, frac))\n    return {mn} + frac * ({mx} - {mn})",
 "digital_display":"def read(features):\n    return float(features['digits_value'])",
 "indicator_light":"def read(features):\n    return 1.0 if features['brightness'] >= {thr} else 0.0",
 "switch":"def read(features):\n    return 1.0 if features['brightness'] >= {thr} else 0.0",
}
def _template(inst):
    t=TEMPLATES.get(inst["type"], TEMPLATES["gauge"]); cal=inst.get("calibration") or {}
    return t.format(min_a=cal.get("min_angle_deg",-120), max_a=cal.get("max_angle_deg",120), mn=inst["range"]["min"], mx=inst["range"]["max"], thr=cal.get("threshold",0.5))
def _reader_type(inst): return {"gauge":"needle_angle","thermometer":"needle_angle","digital_display":"seven_segment_ocr","indicator_light":"light_intensity","switch":"switch_state"}.get(inst["type"],"generic_vision")
def _safe(code):
    return code and "import" not in code and "__" not in code and "def read(features):" in code and len(code)<2000
def run_compiled(compiled, features):
    ns={}; exec(compiled["code"], {"__builtins__":{"max":max,"min":min,"float":float,"abs":abs}}, ns); return float(ns["read"](features))
def features_for(inst, value):
    mn,mx=inst["range"]["min"],inst["range"]["max"]; cal=inst.get("calibration") or {}
    frac=(value-mn)/(mx-mn) if mx>mn else 0
    if inst["type"] in ("gauge","thermometer"): return {"needle_angle_deg": cal.get("min_angle_deg",-120)+frac*(cal.get("max_angle_deg",120)-cal.get("min_angle_deg",-120))}
    if inst["type"]=="digital_display": return {"digits_value":value}
    return {"brightness": float(value)}
def verify(inst, compiled):
    mn,mx=inst["range"]["min"],inst["range"]["max"]; samples=[]; errs=[]
    for i in range(8):
        raw=mn+(mx-mn)*i/7
        expected=(1.0 if raw>=(mn+mx)/2 else 0.0) if inst["type"] in ("indicator_light","switch") else raw
        try: got=run_compiled(compiled, features_for(inst, raw))
        except Exception: got=mn
        errs.append(abs(got-expected)); samples.append({"expected":round(expected,2),"got":round(got,2)})
    mae=sum(errs)/len(errs); rng=max(mx-mn,1e-9); acc=max(0.0,100-mae/rng*100)
    return {"mae":round(mae,4),"max_error":round(max(errs),4),"accuracy_pct":round(acc,2),"passed":acc>=95,"n":len(samples),"samples":samples}
def compile_reader(inst, client=None):
    code=_template(inst); gen="local template (fallback)"
    if client is not None:
        try:
            prompt=(f"Write ONLY Python code `def read(features):` (no imports, no markdown fences, no explanation). It CONVERTS a sensor feature INTO the instrument value. Instrument: {inst['type']}, unit={inst['unit']}, value range {inst['range']['min']}..{inst['range']['max']}, calibration={inst.get('calibration')}. For gauge/thermometer: features['needle_angle_deg'] goes from min_angle_deg at value-min to max_angle_deg at value-max, linearly interpolate and clamp, RETURN THE VALUE (not the angle). For digital_display: return float(features['digits_value']) clamped. For indicator_light/switch: return 1.0 if features['brightness']>=0.5 else 0.0.")
            out=client.spark([{"role":"user","content":prompt}], max_tokens=4000)
            cand=re.search(r"def read\(features\):.*", out, re.S)
            if cand and _safe(cand.group(0)):
                test={"instrument_id":inst["id"],"code":cand.group(0)}
                run_compiled(test, features_for(inst,(inst["range"]["min"]+inst["range"]["max"])/2))
                if verify(inst, test)["passed"]: code=cand.group(0); gen="muse-spark-1.3"
                else: gen="local template (fallback: Muse Spark candidate failed verification)"
        except Exception: pass
    compiled={"instrument_id":inst["id"],"reader_type":_reader_type(inst),"code":code,"generated_by":gen}
    compiled["verification"]=verify(inst, compiled); return compiled
def _extract_json(text):
    m=re.search(r"\[.*\]", text, re.S)
    if not m: raise ValueError("no json")
    return json.loads(m.group(0))
def detect_instruments(image_data_url, client=None):
    sam_boxes=[]
    if client is not None and image_data_url:
        # SAM 3.1 first (per concept) - boxes kept with their concept so
        # they can be mapped directly onto Spark-classified instruments
        sam_found=[]; sam_by_concept={}
        CONCEPTS={"gauge":"pressure gauge","thermometer":"thermometer","digital_display":"digital display","indicator_light":"indicator light","switch":"switch"}
        for typ, concept in CONCEPTS.items():
            try:
                boxes=client.sam_segment(image_data_url, concept)
                sam_by_concept[typ]=boxes; sam_found += boxes
            except Exception: pass
        # Muse Spark vision whole-frame
        try:
            content=[{"type":"text","text":"List every instrument (gauge, digital_display, indicator_light, switch, thermometer) in this panel image. Reply ONLY with a JSON array matching: [{\"id\":\"gauge-1\",\"label\":\"...\",\"type\":\"gauge\",\"unit\":\"PSI\",\"range\":{\"min\":0,\"max\":100},\"bbox\":{\"x\":0.0,\"y\":0.0,\"w\":0.2,\"h\":0.2},\"confidence\":0.9,\"calibration\":{\"min_angle_deg\":-120,\"max_angle_deg\":120}}]. Coordinates normalized 0..1."},{"type":"image_url","image_url":{"url":image_data_url}}]
            out=client.spark([{"role":"user","content":content}], max_tokens=1500)
            items=_extract_json(out); valid=[]
            for i,it in enumerate(items):
                if it.get("type") not in TEMPLATES: continue
                it.setdefault("id",f"inst-{i+1}"); it.setdefault("label",it["type"]); it.setdefault("unit",""); it.setdefault("confidence",0.8)
                it["range"]={"min":float(it.get("range",{}).get("min",0)),"max":float(it.get("range",{}).get("max",100))}
                b=it.get("bbox",{}); it["bbox"]={k:max(0,min(1,float(b.get(k,0.1)))) for k in ("x","y","w","h")}
                it.setdefault("calibration",{"min_angle_deg":-120,"max_angle_deg":120} if it["type"] in ("gauge","thermometer") else {}); it["source"]="sam+spark" if sam_found else "spark-vision"; it.setdefault("track_id",i+1); valid.append(it)
            sam_boxes.extend(sam_found)
            if valid:
                for v in valid:
                    v["sam_boxes"]=len(sam_found)
                    pool=sam_by_concept.get(v["type"]) or sam_found
                    if pool:
                        # nearest SAM box (by centre) becomes THE instrument bbox;
                        # Spark's box is retained for the overlay comparison
                        vc=(v["bbox"]["x"]+v["bbox"]["w"]/2, v["bbox"]["y"]+v["bbox"]["h"]/2)
                        best=min(pool, key=lambda b: (b["bbox"]["x"]+b["bbox"]["w"]/2-vc[0])**2 + (b["bbox"]["y"]+b["bbox"]["h"]/2-vc[1])**2)
                        v["spark_bbox"]=dict(v["bbox"]); v["bbox"]=dict(best["bbox"])
                        v["confidence"]=best.get("confidence", v["confidence"])
                        if best.get("track_id") is not None: v["track_id"]=best["track_id"]
                        v["source"]="sam+spark"
                return valid, valid[0]["source"]
        except Exception: pass
    return [dict(x) for x in DEMO_INSTRUMENTS], "demo-fallback"
