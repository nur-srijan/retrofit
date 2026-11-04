from backend.readers import DEMO_INSTRUMENTS, compile_reader, run_compiled, features_for
from backend.agent import parse_rule
from backend.store import Store
import time
def test_compile_all():
    for inst in DEMO_INSTRUMENTS:
        c=compile_reader(inst, None); assert c["verification"]["passed"], c
        mid=(inst["range"]["min"]+inst["range"]["max"])/2
        expected=(1.0 if mid>=0.5 else 0.0) if inst["type"] in ("indicator_light","switch") else mid
        assert abs(run_compiled(c, features_for(inst, mid))-expected) < 1e-6
def test_rule_regex():
    r=parse_rule("alert when pressure goes above 80", DEMO_INSTRUMENTS, None)
    assert r["instrument_id"]=="gauge-1" and r["op"]==">" and r["threshold"]==80
def test_store_stats():
    s=Store()
    for i in range(5): s.add_reading({"instrument_id":"gauge-1","ts":time.time()+i,"value":float(i*10),"unit":"PSI","quality":"simulated"})
    st=s.stats("gauge-1"); assert st["current"]==40 and st["change"]==40
