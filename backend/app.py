import os, time, math, random, asyncio, base64, json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from backend.meta_clients import MetaClient
from backend.readers import DEMO_INSTRUMENTS, detect_instruments, compile_reader, run_compiled, features_for
from backend.store import Store
from backend.agent import parse_rule, check_rules, why_query, voice_log

app=FastAPI(title="Retrofit")
client=MetaClient(); store=Store()
state={"instruments":[dict(x) for x in DEMO_INSTRUMENTS],"compiled":{},"rules":[],"demo":False,"t0":time.time(),"clients":set(),"alert_cooldown":{}}
FALLBACKS=["SAM 3.1 -> Spark vision -> demo instruments","Spark reader code -> local templates","Spark Open (Baseten) -> muse-spark-1.3 -> regex parser","Wonder -> local stats","Voice Transcribe -> browser Web Speech"]

async def broadcast(ev):
    dead=[]
    for ws in list(state["clients"]):
        try: await ws.send_json(ev)
        except Exception: dead.append(ws)
    for ws in dead: state["clients"].discard(ws)

def demo_value(inst, t):
    el=t-state["t0"]
    if inst["id"]=="gauge-1": return max(0,min(100, 55+35*math.sin(el/18)+random.uniform(-2,2) + (18*math.sin(el/90))))  # drifts, crosses 80 for alert demo
    if inst["id"]=="thermo-1": return max(0,min(100, 42+10*math.sin(el/45+1)+random.uniform(-0.5,0.5)))
    if inst["id"]=="stopwatch-1": return el % 60
    if inst["id"]=="light-1": return 1.0 if (el//12)%2==0 else 0.0
    return (inst["range"]["min"]+inst["range"]["max"])/2

async def incident_agent(ev):
    """Muse Spark Open (Baseten) writes the incident summary - second load-bearing Spark Open job."""
    try:
        content,src=client.spark_open([{"role":"user","content":f"Write a one-sentence operator incident summary + recommended action for this alert. Alert: {ev['message']}. Latest: {store.latest()}"}], max_tokens=2000)
        msg=content
        if not msg: msg,src=f"Incident: {ev['message']} - check the panel.", src+" (empty response; local summary)"
    except Exception:
        msg,src=f"Incident: {ev['message']} - check the panel.", "local template (Spark Open unavailable)"
    out={"kind":"incident","ts":time.time(),"message":msg,"source_model":src,"rule_id":ev.get("rule_id")}
    store.add_event(out); await broadcast(out)

async def simulator():
    while True:
        if state["demo"]:
            now=time.time()
            for inst in state["instruments"]:
                comp=state["compiled"].get(inst["id"]) or compile_reader(inst, None)
                state["compiled"][inst["id"]]=comp
                try: val=run_compiled(comp, features_for(inst, demo_value(inst, now)))
                except Exception: val=demo_value(inst, now)
                if inst["type"]=="digital_display": val=round(val,1)
                elif inst["type"]=="indicator_light": val=float(val)
                else: val=round(float(val),2)
                r={"instrument_id":inst["id"],"ts":now,"value":val,"unit":inst["unit"],"quality":"simulated"}
                store.add_reading(r); await broadcast({"kind":"reading","ts":now,"reading":r})
            for ev in check_rules(state["rules"], store.latest()):
                key=ev["rule_id"]
                if now-state["alert_cooldown"].get(key,0)>15:
                    state["alert_cooldown"][key]=now; store.add_event(ev); await broadcast(ev); asyncio.create_task(incident_agent(ev))
        await asyncio.sleep(1)

@app.on_event("startup")
async def start(): asyncio.create_task(simulator())

@app.get("/api/health")
def health(): return {"status":"ok","models":client.status(),"fallbacks":FALLBACKS,"demo":state["demo"],"instruments":len(state["instruments"])}

@app.post("/api/detect")
async def detect(req: Request):
    body=await req.json(); instruments,source=detect_instruments(body.get("image",""), client)
    state["instruments"]=instruments; return {"instruments":instruments,"source":source}

@app.post("/api/compile")
async def compile_ep(req: Request):
    body=await req.json(); inst=body.get("instrument") or next((i for i in state["instruments"] if i["id"]==body.get("instrument_id")),None)
    if not inst: raise HTTPException(404,"instrument not found")
    comp=compile_reader(inst, client); state["compiled"][inst["id"]]=comp; return comp

@app.get("/api/schema")
def schema(): return {"instruments":state["instruments"],"types":{i["id"]:("boolean" if i["type"] in ("indicator_light","switch") else "number") for i in state["instruments"]}}

@app.get("/api/readings")
def readings(limit:int=200): return {"readings":{i["id"]:store.history(i["id"],limit) for i in state["instruments"]},"latest":store.latest(),"stats":store.all_stats()}

@app.post("/api/demo/start")
def demo_start(): state["demo"]=True; state["t0"]=time.time(); return {"ok":True,"demo":True}
@app.post("/api/demo/stop")
def demo_stop(): state["demo"]=False; return {"ok":True,"demo":False}

@app.post("/api/rules")
async def add_rule(req: Request):
    body=await req.json()
    try: rule=parse_rule(body.get("text",""), state["instruments"], client)
    except ValueError as e: raise HTTPException(400,str(e))
    state["rules"].append(rule); return rule
@app.get("/api/rules")
def list_rules(): return {"rules":state["rules"]}
@app.delete("/api/rules/{rule_id}")
def del_rule(rule_id:str): state["rules"]=[r for r in state["rules"] if r["id"]!=rule_id]; return {"ok":True}

@app.post("/api/why")
async def why(req: Request):
    body=await req.json(); return why_query(body.get("question","Why did pressure drop?"), store, client, store.recent_events())

@app.post("/api/voice")
async def voice(req: Request):
    body=await req.json()
    try:
        audio=base64.b64decode(body["audio_base64"]) if body.get("audio_base64") else None
        ev=voice_log(body.get("transcript"), client, audio)
    except Exception as e: raise HTTPException(400,str(e))
    store.add_event(ev); await broadcast(ev); return ev

@app.get("/api/events")
def events(): return {"events":store.recent_events()}

@app.websocket("/ws/stream")
async def ws(ws: WebSocket):
    await ws.accept(); state["clients"].add(ws)
    try:
        while True: await ws.receive_text()
    except Exception: state["clients"].discard(ws)

app.mount("/static", StaticFiles(directory="frontend"), name="static")
@app.get("/")
def index(): return FileResponse("frontend/index.html")

if __name__=="__main__":
    import uvicorn; uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT","8000")))
