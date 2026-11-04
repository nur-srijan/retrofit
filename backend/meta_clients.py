import os, json, urllib.request, urllib.error, uuid

def _load_dotenv():
    for path in (".env", os.path.join(os.path.dirname(__file__),"..",".env")):
        try:
            with open(path) as f:
                for line in f:
                    line=line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k,v=line.split("=",1); os.environ.setdefault(k.strip(), v.strip())
        except FileNotFoundError: pass
_load_dotenv()

BASE=os.environ.get("META_BASE_URL","https://api.meta.ai/v1").rstrip("/")
class MetaClient:
    def __init__(self):
        self.key=os.environ.get("MODEL_API_KEY","")
        self.baseten_key=os.environ.get("BASETEN_API_KEY","")
        self.baseten_base=os.environ.get("BASETEN_BASE_URL","https://inference.baseten.co/v1").rstrip("/")
        self.spark_open_model=os.environ.get("SPARK_OPEN_MODEL","meta-models/muse-spark-open-1026")
    def _post(self, url, payload, key, timeout=90):
        req=urllib.request.Request(url, data=json.dumps(payload).encode(), headers={"Authorization":f"Bearer {key}","Content-Type":"application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=timeout) as r: return json.loads(r.read())
    def chat(self, model, messages, max_tokens=2000):
        if not self.key: raise RuntimeError("MODEL_API_KEY not set")
        out=self._post(f"{BASE}/chat/completions", {"model":model,"messages":messages,"max_tokens":max_tokens}, self.key)
        return (out["choices"][0]["message"].get("content") or "").strip()
    def spark(self, messages, max_tokens=2000): return self.chat("muse-spark-1.3", messages, max_tokens)
    def wonder(self, messages, max_tokens=2000): return self.chat("muse-wonder-1.0", messages, max_tokens)
    def spark_open(self, messages, max_tokens=1200):
        if self.baseten_key:
            try:
                out=self._post(f"{self.baseten_base}/chat/completions", {"model":self.spark_open_model,"messages":messages,"max_tokens":max_tokens}, self.baseten_key)
                return (out["choices"][0]["message"].get("content") or "").strip(), f"{self.spark_open_model} via Baseten"
            except Exception: pass
        return self.chat("muse-spark-1.3", messages, max_tokens), "muse-spark-1.3 via Meta API (fallback: BASETEN_API_KEY not set/working; intended meta-models/muse-spark-open-1026 via Baseten)"
    def sam_segment(self, image_data_url, concept):
        """SAM 3.1 via /responses streaming. Segmentation is special-token text; unparseable/empty -> []."""
        if not self.key: return []
        payload={"model":"sam-3.1","stream":True,"input":[{"type":"message","role":"user","content":[{"type":"input_text","text":concept},{"type":"input_image","image_url":image_data_url}]}]}
        req=urllib.request.Request(f"{BASE}/responses", data=json.dumps(payload).encode(), headers={"Authorization":f"Bearer {self.key}","Content-Type":"application/json"}, method="POST")
        text=""
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                for line in resp:
                    s=line.decode(errors="ignore").strip()
                    if s.startswith("data:"):
                        try:
                            d=json.loads(s[5:]); 
                            if d.get("type")=="response.output_text.done": text=d.get("text","")
                        except Exception: pass
        except Exception: return []
        from backend.sam_parser import parse_sam_text
        return parse_sam_text(text)
    def transcribe(self, audio_bytes, filename="audio.webm"):
        if not self.key: raise RuntimeError("MODEL_API_KEY not set")
        boundary="----retrofit"+uuid.uuid4().hex
        parts=[]
        def field(name, val): parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\"\r\n\r\n{val}\r\n".encode())
        field("model","muse-voice-transcribe-1.0"); field("language","en"); field("output_format","json")
        parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{filename}\"\r\nContent-Type: audio/webm\r\n\r\n".encode()+audio_bytes+b"\r\n")
        parts.append(f"--{boundary}--\r\n".encode())
        req=urllib.request.Request(f"{BASE}/asr/transcribe", data=b"".join(parts), headers={"Authorization":f"Bearer {self.key}","Content-Type":f"multipart/form-data; boundary={boundary}"}, method="POST")
        with urllib.request.urlopen(req, timeout=90) as r: out=json.loads(r.read())
        return out.get("text") or out.get("transcript") or str(out)
    def status(self):
        return {"meta_key_present":bool(self.key),"baseten_key_present":bool(self.baseten_key),"spark_open_source":f"{self.spark_open_model} via Baseten" if self.baseten_key else "fallback muse-spark-1.3 (set BASETEN_API_KEY for Spark Open)","meta_base":BASE}
