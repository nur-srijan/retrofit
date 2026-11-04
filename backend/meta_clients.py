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
    def _to_wav16k(self, audio_bytes, filename):
        if audio_bytes[:4]==b"RIFF": return audio_bytes
        import shutil, subprocess, tempfile
        ffmpeg=shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
        if not shutil.which(ffmpeg) and not os.path.exists(ffmpeg): raise RuntimeError("ffmpeg required to convert browser audio to WAV")
        suffix=os.path.splitext(filename)[1] or ".webm"
        with tempfile.TemporaryDirectory() as d:
            src=os.path.join(d,"in"+suffix); dst=os.path.join(d,"out.wav")
            open(src,"wb").write(audio_bytes)
            subprocess.run([ffmpeg,"-y","-i",src,"-ac","1","-ar","16000","-sample_fmt","s16",dst], check=True, capture_output=True)
            return open(dst,"rb").read()
    def transcribe(self, audio_bytes, filename="audio.webm"):
        """Muse Voice Transcribe: multipart 'request'+'audio' (verified live).
        request must be exactly {model, audioEncoding:WAV}; extra fields -> 400."""
        if not self.key: raise RuntimeError("MODEL_API_KEY not set")
        audio_bytes=self._to_wav16k(audio_bytes, filename); filename="audio.wav"
        boundary="----retrofit"+uuid.uuid4().hex
        ctype="audio/wav"
        request_json=json.dumps({"model":"muse-voice-transcribe-1.0","audioEncoding":"WAV"})
        parts=[
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"request\"\r\nContent-Type: application/json\r\n\r\n{request_json}\r\n".encode(),
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"audio\"; filename=\"{filename}\"\r\nContent-Type: {ctype}\r\n\r\n".encode()+audio_bytes+b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ]
        req=urllib.request.Request(f"{BASE}/asr/transcribe", data=b"".join(parts), headers={"Authorization":f"Bearer {self.key}","Content-Type":f"multipart/form-data; boundary={boundary}"}, method="POST")
        with urllib.request.urlopen(req, timeout=90) as r: out=json.loads(r.read())
        text=out.get("text") or out.get("transcript") or ""
        if not text and isinstance(out.get("result"), dict): text=out["result"].get("text","")
        if not text: raise RuntimeError(f"transcribe returned no text: {str(out)[:200]}")
        return text
    def status(self):
        return {"meta_key_present":bool(self.key),"baseten_key_present":bool(self.baseten_key),"spark_open_source":f"{self.spark_open_model} via Baseten" if self.baseten_key else "fallback muse-spark-1.3 (set BASETEN_API_KEY for Spark Open)","meta_base":BASE}
