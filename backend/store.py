import threading, time, statistics
from collections import deque
class Store:
    def __init__(self):
        self.lock=threading.Lock(); self.data={}; self.events=deque(maxlen=200)
    def add_reading(self,r):
        with self.lock: self.data.setdefault(r["instrument_id"],deque(maxlen=2000)).append(r)
    def latest(self):
        with self.lock: return {k:v[-1] for k,v in self.data.items() if v}
    def history(self,iid,limit=200):
        with self.lock: return list(self.data.get(iid,[]))[-limit:]
    def stats(self,iid):
        h=self.history(iid,500)
        if not h: return None
        vals=[float(x["value"]) for x in h if isinstance(x["value"],(int,float))]
        if not vals: return {"count":len(h),"current":h[-1]["value"]}
        dt=max((h[-1]["ts"]-h[0]["ts"])/60,1e-9) if len(h)>1 else 0
        return {"count":len(vals),"current":vals[-1],"min":min(vals),"max":max(vals),"mean":round(statistics.mean(vals),3),"first":vals[0],"last":vals[-1],"change":round(vals[-1]-vals[0],3),"trend_per_min":round((vals[-1]-vals[0])/dt,3) if dt else 0,"std":round(statistics.pstdev(vals),3) if len(vals)>1 else 0}
    def all_stats(self): return {k:self.stats(k) for k in list(self.data.keys())}
    def add_event(self,e):
        with self.lock: self.events.append(e)
    def recent_events(self,limit=50): return list(self.events)[-limit:]
    def to_csv(self):
        with self.lock:
            rows=["timestamp_iso,timestamp_unix,instrument_id,value,unit,quality"]
            all_r=[]
            for dq in self.data.values(): all_r.extend(list(dq))
            all_r.sort(key=lambda x: x.get("ts", 0))
            for r in all_r:
                iso=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(r.get("ts",0)))
                rows.append(f"{iso},{r.get('ts',0):.3f},{r.get('instrument_id','')},{r.get('value','')},{r.get('unit','')},{r.get('quality','')}")
            return "\n".join(rows)
