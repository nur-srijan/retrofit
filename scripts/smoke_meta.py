import os, json, urllib.request, urllib.error, base64, time
KEY=os.environ.get("MODEL_API_KEY","")
print("key present:", bool(KEY), "prefix:", KEY[:4] if KEY else "")
def post(path, payload, timeout=60):
    req=urllib.request.Request("https://api.meta.ai/v1"+path, data=json.dumps(payload).encode(), headers={"Authorization":f"Bearer {KEY}","Content-Type":"application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode()[:2000]
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:2000]
    except Exception as e:
        return None, str(e)

for model in ["muse-spark-1.3","muse-wonder-1.0"]:
    s,b=post("/chat/completions", {"model":model,"messages":[{"role":"user","content":"Reply with exactly: OK"}],"max_tokens":20})
    print(f"\n== {model} chat == status={s}\n{b[:800]}")

# SAM smoke: tiny 64x64 red circle PNG generated via zlib
import struct, zlib
def png(w,h):
    raw=b""
    for y in range(h):
        raw+=b"\x00"+bytes([200,30,30]*w)
    def chunk(t,d):
        c=t+d; return struct.pack(">I",len(d))+c+struct.pack(">I",zlib.crc32(c)&0xffffffff)
    return b"\x89PNG\r\n\x1a\n"+chunk(b"IHDR",struct.pack(">IIBBBBB",w,h,8,2,0,0,0))+chunk(b"IDAT",zlib.compress(raw))+chunk(b"IEND",b"")
data="data:image/png;base64,"+base64.b64encode(png(64,64)).decode()
s,b=post("/responses", {"model":"sam-3.1","stream":False,"input":[{"type":"message","role":"user","content":[{"type":"input_text","text":"red square"},{"type":"input_image","image_url":data}]}]}, timeout=90)
print(f"\n== sam-3.1 responses == status={s}\n{b[:1200]}")

# models list
req=urllib.request.Request("https://api.meta.ai/v1/models", headers={"Authorization":f"Bearer {KEY}"})
try:
    with urllib.request.urlopen(req, timeout=30) as r: print("\n== /models ==", r.status, r.read().decode()[:1500])
except Exception as e: print("\n== /models err ==", e)
